"""
Quick test script - downloads just 4 tiles to verify setup.
Run this first before the full download.
"""
import os
import sys
import math
import yaml
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("SENTINELHUB_CLIENT_ID") or os.environ.get("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SENTINELHUB_CLIENT_SECRET") or os.environ.get("COPERNICUS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    sys.exit("❌ Set SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET in .env")

TOKEN_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

# Small test bbox around Singapore
TEST_BBOX = [103.6, 1.2, 104.1, 1.5]  # Small area around Singapore

OUTPUT_DIR = Path("tiles_test")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Sentinel-2 Tile Downloader - TEST MODE")
print("=" * 60)
print(f"Test bbox: {TEST_BBOX}")
print(f"Output: {OUTPUT_DIR}/")

# Get token
print("\n1. Getting token...")
r = requests.post(TOKEN_URL, auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                  data={"grant_type": "client_credentials"}, timeout=30)
if not r.ok:
    sys.exit(f"❌ Token error {r.status_code}: {r.text}")

token = r.json()["access_token"]
print(f"✓ Token obtained (length: {len(token)})")

# Download single test tile
print("\n2. Downloading test tile...")
body = {
    "input": {
        "bounds": {"bbox": TEST_BBOX},
        "data": [{
            "type": "sentinel-2-l2a",
            "dataFilter": {"maxCloudCoverage": 30}
        }]
    },
    "output": {
        "width": 512,
        "height": 512,
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
resp = requests.post(PROCESS_URL, headers=hdrs, json=body, stream=True, timeout=120)

if resp.status_code == 200:
    output_path = OUTPUT_DIR / "test_tile.png"
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    print(f"✓ Test tile saved to: {output_path}")
    
    # Create simple manifest
    manifest = {
        "test_mode": True,
        "bbox": TEST_BBOX,
        "center": {
            "longitude": (TEST_BBOX[0] + TEST_BBOX[2]) / 2,
            "latitude": (TEST_BBOX[1] + TEST_BBOX[3]) / 2
        },
        "filename": "test_tile.png",
        "size_px": 512
    }
    
    manifest_path = OUTPUT_DIR / "test_manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)
    print(f"✓ Manifest saved to: {manifest_path}")
    
    print("\n" + "=" * 60)
    print("✓ TEST SUCCESSFUL!")
    print("=" * 60)
    print("\nYou can now run the full download:")
    print("  python download_tiles.py")
    
else:
    print(f"❌ Download failed: {resp.status_code}")
    print(resp.text)
    sys.exit(1)
