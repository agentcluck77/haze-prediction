"""
High-resolution tiled Sentinel-2 downloader with proper rate limiting.

Follows Sentinel Hub rate limiting best practices:
- Respects Retry-After headers
- Implements exponential backoff
- Spreads requests over time (ramp-up)
- Caches tokens until expiry
"""
import os
import math
import time
import yaml
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime
import random

load_dotenv()

# Configuration
CLIENT_ID = os.environ.get("SENTINELHUB_CLIENT_ID") or os.environ.get("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SENTINELHUB_CLIENT_SECRET") or os.environ.get("COPERNICUS_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Set SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET in environment")

TOKEN_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

# SE Asia region bbox [west, south, east, north]
BBOX_FULL = [95.038077, -6.419254, 117.950162, 4.370021]

# Target resolution (meters per pixel)
TARGET_MPP = 100.0  # Adjustable: 10-1500

# Output directory
OUTPUT_DIR = Path("tiles")
OUTPUT_DIR.mkdir(exist_ok=True)

# Rate limiting configuration (following Sentinel Hub best practices)
# Spread requests evenly: if limit is 600/min, send 1 request every 0.1s
MIN_REQUEST_INTERVAL = 0.1  # seconds between requests (10 req/s max burst)
MAX_RETRIES = 5  # Maximum retry attempts for 429 errors
INITIAL_BACKOFF = 1.0  # Initial backoff delay in seconds


def meters_per_degree(lat_deg):
    """Approximate meters per degree at given latitude."""
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 110574.0
    m_per_deg_lon = 111320.0 * math.cos(lat_rad)
    return m_per_deg_lat, m_per_deg_lon


def compute_tile_size_degrees(lat_mean, target_mpp, tile_size_px=2500):
    """Compute the bbox size in degrees for a tile."""
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
            
            tiles.append((tile_bbox, center_lon, center_lat))
            
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
                print(f"  Rate limited on token request. Waiting {retry_after:.1f}s...")
                time.sleep(retry_after)
                continue
            
            r.raise_for_status()
            token_data = r.json()
            return token_data["access_token"], token_data.get("expires_in", 3600)
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                print(f"  Token request failed (attempt {attempt+1}/{MAX_RETRIES}). Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                raise


def download_tile_with_retry(token, bbox, tile_size_px, output_path):
    """
    Download a single tile with exponential backoff retry.
    
    Returns:
        (success: bool, retry_after_ms: int or None)
    """
    body = {
        "input": {
            "bounds": {"bbox": bbox},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "maxCloudCoverage": 30
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
            
            # Handle rate limiting (429)
            if resp.status_code == 429:
                retry_after_ms = int(resp.headers.get("retry-after", INITIAL_BACKOFF * 1000))
                retry_after_s = retry_after_ms / 1000.0
                
                print(f"    Rate limited (429). Waiting {retry_after_s:.1f}s (attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(retry_after_s)
                continue
            
            # Handle success
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True, None
            
            # Handle other errors
            if resp.status_code >= 500:
                # Server error - retry with exponential backoff
                if attempt < MAX_RETRIES - 1:
                    backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                    print(f"    Server error {resp.status_code}. Retrying in {backoff:.1f}s (attempt {attempt+1}/{MAX_RETRIES})...")
                    time.sleep(backoff)
                    continue
                else:
                    print(f"    Error {resp.status_code} (max retries exceeded): {resp.text[:200]}")
                    return False, None
            else:
                # Client error (4xx other than 429) - don't retry
                print(f"    Error {resp.status_code}: {resp.text[:200]}")
                return False, None
                
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                print(f"    Timeout. Retrying in {backoff:.1f}s (attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(backoff)
                continue
            else:
                print(f"    Timeout (max retries exceeded)")
                return False, None
                
        except Exception as e:
            print(f"    Exception: {e}")
            return False, None
    
    return False, None


def main():
    print("=" * 70)
    print("Sentinel-2 High-Resolution Tiled Downloader (Rate-Limit Aware)")
    print("=" * 70)
    print(f"\nFull bbox: {BBOX_FULL}")
    print(f"Target resolution: {TARGET_MPP} m/px")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Request interval: {MIN_REQUEST_INTERVAL}s (ramp-up compliant)")
    
    # Split bbox into tiles
    tile_size_px = 2500
    tiles = split_bbox_into_tiles(BBOX_FULL, TARGET_MPP, tile_size_px)
    
    print(f"\nTotal tiles to download: {len(tiles)}")
    print(f"Tile size: {tile_size_px}x{tile_size_px} pixels")
    print(f"Estimated time: {len(tiles) * MIN_REQUEST_INTERVAL / 60:.1f} minutes (without rate limits)")
    
    # Get initial token
    print("\nObtaining access token...")
    token, expires_in = get_token()
    token_expiry = time.time() + expires_in - 300  # Refresh 5 min before expiry
    print(f"Token obtained (expires in {expires_in}s)")
    
    # Download tiles
    manifest = {
        "metadata": {
            "bbox_full": BBOX_FULL,
            "target_mpp": TARGET_MPP,
            "tile_size_px": tile_size_px,
            "total_tiles": len(tiles),
            "download_timestamp": datetime.utcnow().isoformat() + "Z",
            "rate_limit_config": {
                "min_request_interval": MIN_REQUEST_INTERVAL,
                "max_retries": MAX_RETRIES
            }
        },
        "tiles": []
    }
    
    successful = 0
    failed = 0
    last_request_time = 0
    
    print("\nDownloading tiles (with rate limiting)...")
    print("-" * 70)
    
    for idx, (tile_bbox, center_lon, center_lat) in enumerate(tiles, 1):
        # Refresh token if needed
        if time.time() > token_expiry:
            print("\n  Refreshing token...")
            token, expires_in = get_token()
            token_expiry = time.time() + expires_in - 300
        
        # Rate limiting: ensure minimum interval between requests (ramp-up)
        elapsed = time.time() - last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            sleep_time = MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        
        # Generate filename
        filename = f"tile_{idx:04d}.png"
        output_path = OUTPUT_DIR / filename
        
        print(f"[{idx}/{len(tiles)}] {filename} (center: {center_lon:.4f}, {center_lat:.4f})")
        
        # Download tile with retry logic
        last_request_time = time.time()
        success, retry_after = download_tile_with_retry(token, tile_bbox, tile_size_px, output_path)
        
        if success:
            successful += 1
            manifest["tiles"].append({
                "filename": filename,
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
    manifest_path = "tiles_manifest.yaml"
    with open(manifest_path, "w", encoding="utf8") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    
    print("\n" + "=" * 70)
    print("Download complete!")
    print(f"Successful: {successful}/{len(tiles)}")
    print(f"Failed: {failed}/{len(tiles)}")
    print(f"Manifest saved to: {manifest_path}")
    print(f"Tiles saved to: {OUTPUT_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
