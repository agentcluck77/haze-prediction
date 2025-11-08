import os
import math
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# Use env vars for secrets (never hardcode)
CLIENT_ID = os.environ.get("SENTINELHUB_CLIENT_ID") or os.environ.get("COPERNICUS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SENTINELHUB_CLIENT_SECRET") or os.environ.get("COPERNICUS_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Set SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET (or COPERNICUS_CLIENT_*) in environment")

# If you are calling Sentinel-Hub services, use their token endpoint. If using Dataspace endpoints, use the corresponding endpoint.
TOKEN_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

# Correct bbox order: [west, south, east, north] (lon_min, lat_min, lon_max, lat_max)
# Your intended area seems to be lon range 95..117 and lat range -6..4
bbox = [95.038077, -6.419254, 117.950162, 4.370021]

# collection limit (meters per pixel)
MAX_MPP = 1450.0

def meters_per_degree(lat_deg):
    # Approximate meters per degree at given latitude
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 110574.0
    m_per_deg_lon = 111320.0 * math.cos(lat_rad)
    return m_per_deg_lat, m_per_deg_lon

# compute approximate ground width/height (meters) using mean latitude
lon_min, lat_min, lon_max, lat_max = bbox
lat_mean = (lat_min + lat_max) / 2.0
m_deg_lat, m_deg_lon = meters_per_degree(lat_mean)
ground_width_m = (lon_max - lon_min) * m_deg_lon
ground_height_m = (lat_max - lat_min) * m_deg_lat

# choose width/height so meters-per-pixel <= MAX_MPP
width_px = max(1, math.ceil(ground_width_m / MAX_MPP))
height_px = max(1, math.ceil(ground_height_m / MAX_MPP))

# ensure actual m/px does not slightly exceed MAX_MPP (fix rounding edge cases)
def current_mpp(w, h):
    return max(ground_width_m / w, ground_height_m / h)

# increment the dimension that currently violates the limit until it's within allowed range
MAX_PIX = 8192
while current_mpp(width_px, height_px) > MAX_MPP:
    if (ground_width_m / width_px) >= (ground_height_m / height_px):
        width_px += 1
    else:
        height_px += 1
    # guard against runaway sizes
    if width_px > MAX_PIX or height_px > MAX_PIX:
        break

# clamp to reasonable limits (adjust if needed)
width_px = min(width_px, MAX_PIX)
height_px = min(height_px, MAX_PIX)

print(f"bbox: {bbox}")
print(f"approx ground size: {ground_width_m:.0f} m x {ground_height_m:.0f} m")
print(f"using size: {width_px} x {height_px} -> m/px ≈ {current_mpp(width_px, height_px):.1f} m/px")

# get token (client credentials)
r = requests.post(TOKEN_URL, auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                  data={"grant_type": "client_credentials"}, timeout=30)
r.raise_for_status()
token = r.json()["access_token"]

body = {
    "input": {
        "bounds": {"bbox": bbox},
        "data": [{"type": "sentinel-2-l2a"}]
    },
    "output": {
        "width": int(width_px),
        "height": int(height_px),
        "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
    },
    "evalscript": """
    //VERSION=3
    function setup() { return { input: ["B02","B03","B04"], output: { bands: 3 } }; }
    function evaluatePixel(sample) { return [2.5*sample.B04,2.5*sample.B03,2.5*sample.B02]; }
    """
}

hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
resp = requests.post(PROCESS_URL, headers=hdrs, json=body, stream=True, timeout=120)
if resp.status_code == 200:
    with open("sentinel2_image.png", "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    print("Saved sentinel2_image.png")
else:
    print("Error:", resp.status_code)
    print(resp.text)