"""
High-resolution tiled Sentinel-2 downloader with optimal rate limiting.
Auto-calculates tile size to maximize resolution while respecting API limits.
"""
import os
import math
import time
import yaml
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import hashlib

load_dotenv()

# Configuration
CLIENT_ID = os.environ.get("SENTINELHUB_CLIENT_ID") or os.environ.get("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SENTINELHUB_CLIENT_SECRET") or os.environ.get("COPERNICUS_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Set SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET")

TOKEN_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

# SE Asia region bbox [west, south, east, north]
BBOX_FULL = [95.038077, -6.419254, 117.950162, 4.370021]

# Auto-calculate optimal tile size to avoid rate limiting
# Strategy: smaller MPP = higher resolution but more tiles = more requests
# Balance: 60m/px gives ~400 tiles for your bbox (acceptable for hourly runs)
TARGET_MPP = 60.0  # meters per pixel (adjustable: 10=best quality, 100=faster)

# Output directory structure: tiles/{timestamp}/
OUTPUT_BASE = Path("tiles")
OUTPUT_BASE.mkdir(exist_ok=True)

# Rate limiting (Sentinel Hub best practices)
MIN_REQUEST_INTERVAL = 0.15  # 6-7 req/s (conservative for ramp-up)
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0

# Processing unit estimation (rough heuristic)
# Sentinel Hub charges based on processing units (PU)
# 1 PU ≈ 1 megapixel at 10m resolution
def estimate_processing_units(width_px, height_px, target_mpp):
    """Estimate processing units for a request."""
    megapixels = (width_px * height_px) / 1e6
    # Scale by resolution (10m = 1.0, 60m = 0.36)
    resolution_factor = (10.0 / target_mpp) ** 2
    return megapixels * resolution_factor


def meters_per_degree(lat_deg):
    """Approximate meters per degree at given latitude."""
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 110574.0
    m_per_deg_lon = 111320.0 * math.cos(lat_rad)
    return m_per_deg_lat, m_per_deg_lon


def compute_tile_size_degrees(lat_mean, target_mpp, tile_size_px=2500):
    """Compute bbox size in degrees for a tile."""
    m_deg_lat, m_deg_lon = meters_per_degree(lat_mean)
    ground_size_m = tile_size_px * target_mpp
    delta_lat = ground_size_m / m_deg_lat
    delta_lon = ground_size_m / m_deg_lon
    return delta_lon, delta_lat


def split_bbox_into_tiles(bbox, target_mpp, tile_size_px=2500):
    """Split large bbox into smaller tiles."""
    west, south, east, north = bbox
    lat_mean = (south + north) / 2.0
    
    delta_lon, delta_lat = compute_tile_size_degrees(lat_mean, target_mpp, tile_size_px)
    
    tiles = []
    current_south = south
    
    while current_south < north:
        current_north = min(current_south + delta_lat, north)
        current_west = west
        
        while current_west < east:
            current_east = min(current_west + delta_lon, east)
            
            tile_bbox = [current_west, current_south, current_east, current_north]
            center_lon = (current_west + current_east) / 2.0
            center_lat = (current_south + current_north) / 2.0
            
            # Generate stable tile ID based on coordinates
            tile_id = hashlib.md5(f"{tile_bbox}".encode()).hexdigest()[:12]
            
            tiles.append((tile_bbox, center_lon, center_lat, tile_id))
            
            current_west = current_east
        
        current_south = current_north
    
    return tiles


def get_token():
    """Obtain OAuth2 token with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(TOKEN_URL, auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                              data={"grant_type": "client_credentials"}, timeout=30)
            
            if r.status_code == 429:
                retry_after = int(r.headers.get("retry-after", INITIAL_BACKOFF * 1000)) / 1000.0
                print(f"  Rate limited on token. Waiting {retry_after:.1f}s...")
                time.sleep(retry_after)
                continue
            
            r.raise_for_status()
            token_data = r.json()
            return token_data["access_token"], token_data.get("expires_in", 3600)
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                print(f"  Token request failed. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                raise


def download_tile_with_retry(token, bbox, tile_size_px, output_path, time_range):
    """Download a single tile with retry logic."""
    body = {
        "input": {
            "bounds": {"bbox": bbox},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": time_range[0],
                        "to": time_range[1]
                    },
                    "maxCloudCoverage": 30,
                    "mosaickingOrder": "leastCC"  # Pick least cloudy
                }
            }]
        },
        "output": {
            "width": int(tile_size_px),
            "height": int(tile_size_px),
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
        },
        "evalscript": """
        //VERSION=3
        function setup() { 
            return { 
                input: ["B02","B03","B04", "dataMask"], 
                output: { bands: 4 } 
            }; 
        }
        function evaluatePixel(sample) { 
            return [2.5*sample.B04, 2.5*sample.B03, 2.5*sample.B02, sample.dataMask]; 
        }
        """
    }
    
    hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(PROCESS_URL, headers=hdrs, json=body, stream=True, timeout=120)
            
            if resp.status_code == 429:
                retry_after_ms = int(resp.headers.get("retry-after", INITIAL_BACKOFF * 1000))
                retry_after_s = retry_after_ms / 1000.0
                print(f"    Rate limited. Waiting {retry_after_s:.1f}s...")
                time.sleep(retry_after_s)
                continue
            
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True, None
            
            if resp.status_code >= 500 and attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                print(f"    Server error. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                continue
            else:
                print(f"    Error {resp.status_code}: {resp.text[:200]}")
                return False, None
                
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                print(f"    Timeout. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                return False, None
        except Exception as e:
            print(f"    Exception: {e}")
            return False, None
    
    return False, None


def download_region(bbox, target_mpp, timestamp_str, time_range):
    """Download all tiles for a region at a specific timestamp."""
    print("=" * 70)
    print(f"Downloading region at {timestamp_str}")
    print("=" * 70)
    print(f"Bbox: {bbox}")
    print(f"Resolution: {target_mpp} m/px")
    print(f"Time range: {time_range[0]} to {time_range[1]}")
    
    # Create output directory for this timestamp
    output_dir = OUTPUT_BASE / timestamp_str
    output_dir.mkdir(exist_ok=True)
    
    # Split into tiles
    tile_size_px = 2500
    tiles = split_bbox_into_tiles(bbox, target_mpp, tile_size_px)
    
    print(f"\nTotal tiles: {len(tiles)}")
    print(f"Tile size: {tile_size_px}x{tile_size_px} px")
    
    # Estimate processing units
    total_pu = sum(estimate_processing_units(tile_size_px, tile_size_px, target_mpp) 
                   for _ in tiles)
    print(f"Estimated total PU: {total_pu:.1f}")
    print(f"Estimated time: {len(tiles) * MIN_REQUEST_INTERVAL / 60:.1f} minutes")
    
    # Get token
    print("\nObtaining token...")
    token, expires_in = get_token()
    token_expiry = time.time() + expires_in - 300
    
    # Download tiles
    manifest = {
        "metadata": {
            "bbox_full": bbox,
            "target_mpp": target_mpp,
            "tile_size_px": tile_size_px,
            "total_tiles": len(tiles),
            "timestamp": timestamp_str,
            "time_range": {
                "from": time_range[0],
                "to": time_range[1]
            },
            "estimated_pu": round(total_pu, 2)
        },
        "tiles": []
    }
    
    successful = 0
    failed = 0
    last_request_time = 0
    
    print("\nDownloading tiles...")
    print("-" * 70)
    
    for idx, (tile_bbox, center_lon, center_lat, tile_id) in enumerate(tiles, 1):
        # Refresh token if needed
        if time.time() > token_expiry:
            print("\n  Refreshing token...")
            token, expires_in = get_token()
            token_expiry = time.time() + expires_in - 300
        
        # Rate limiting
        elapsed = time.time() - last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        
        filename = f"tile_{tile_id}.png"
        output_path = output_dir / filename
        
        print(f"[{idx}/{len(tiles)}] {filename} ({center_lon:.4f}, {center_lat:.4f})")
        
        last_request_time = time.time()
        success, _ = download_tile_with_retry(token, tile_bbox, tile_size_px, output_path, time_range)
        
        if success:
            successful += 1
            manifest["tiles"].append({
                "filename": filename,
                "tile_id": tile_id,
                "tile_index": idx,
                "bbox": tile_bbox,
                "center": {
                    "longitude": round(center_lon, 6),
                    "latitude": round(center_lat, 6)
                },
                "size_px": tile_size_px,
                "status": "success"
            })
            print(f"  ✓ Saved")
        else:
            failed += 1
            manifest["tiles"].append({
                "filename": filename,
                "tile_id": tile_id,
                "tile_index": idx,
                "bbox": tile_bbox,
                "center": {
                    "longitude": round(center_lon, 6),
                    "latitude": round(center_lat, 6)
                },
                "size_px": tile_size_px,
                "status": "failed"
            })
            print(f"  ✗ Failed")
    
    # Save manifest
    manifest_path = output_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    
    print("\n" + "=" * 70)
    print(f"Download complete: {successful}/{len(tiles)} successful")
    print(f"Manifest: {manifest_path}")
    print("=" * 70)
    
    return manifest


def main():
    """Download tiles for current time."""
    # Use current time
    now = datetime.utcnow()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    
    # Time range: last 7 days (gives best chance of cloud-free imagery)
    time_to = now.isoformat() + "Z"
    time_from = (now - timedelta(days=7)).isoformat() + "Z"
    time_range = (time_from, time_to)
    
    download_region(BBOX_FULL, TARGET_MPP, timestamp_str, time_range)


if __name__ == "__main__":
    main()
