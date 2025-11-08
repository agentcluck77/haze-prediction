# Sentinel-2 High-Resolution Tiled Downloader

Download high-resolution Sentinel-2 satellite imagery for Southeast Asia region as a grid of tiles.

## Features

- **High Resolution**: Downloads at 100m/pixel (configurable down to 10m for native Sentinel-2 resolution)
- **Automatic Tiling**: Splits large bounding box into manageable tiles
- **YAML Manifest**: Each tile mapped to its center coordinates and bbox
- **Rate Limiting**: Built-in delays to respect API limits
- **Token Management**: Automatic token refresh for long downloads
- **Cloud Filtering**: Max 30% cloud coverage per tile

## Setup

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Set credentials in `.env`:

```
SENTINELHUB_CLIENT_ID=your-client-id
SENTINELHUB_CLIENT_SECRET=your-client-secret
```

## Usage

### Quick Start

```powershell
python download_tiles.py
```

This will:

- Split the SE Asia bbox into ~250km x 250km tiles at 100m/pixel
- Download each tile as a 2500x2500 PNG
- Save tiles to `./tiles/` folder
- Generate `tiles_manifest.yaml` with coordinates

### Configuration

Edit `download_tiles.py` to customize:

```python
# Resolution (lower = higher quality, more tiles)
TARGET_MPP = 100.0  # meters per pixel (10-1500)

# Tile size
tile_size_px = 2500  # pixels (width and height)

# Bounding box [west, south, east, north]
BBOX_FULL = [95.038077, -6.419254, 117.950162, 4.370021]

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # seconds between requests
```

### Resolution Guidelines

- **10m/pixel**: Native Sentinel-2 resolution (RGB bands), generates many tiles
- **100m/pixel**: Good balance of quality and tile count (recommended)
- **500m/pixel**: Lower resolution, fewer tiles, faster download
- **1500m/pixel**: Maximum allowed by Sentinel Hub, very few tiles

## Output

### Tiles Directory

```
tiles/
├── tile_0001.png
├── tile_0002.png
├── tile_0003.png
...
```

### Manifest File (`tiles_manifest.yaml`)

```yaml
metadata:
  bbox_full: [95.038077, -6.419254, 117.950162, 4.370021]
  target_mpp: 100.0
  tile_size_px: 2500
  total_tiles: 144
  download_timestamp: "2025-11-08T..."

tiles:
  - filename: tile_0001.png
    tile_index: 1
    bbox: [95.038077, -6.419254, 98.123456, -3.334567]
    center:
      longitude: 96.580766
      latitude: -4.876910
    size_px: 2500
    status: success
  ...
```

## Using the Tiles

### Load with Python

```python
import yaml
from PIL import Image

# Load manifest
with open("tiles_manifest.yaml") as f:
    manifest = yaml.safe_load(f)

# Load a specific tile
tile = manifest["tiles"][0]
img = Image.open(f"tiles/{tile['filename']}")
center = tile["center"]
print(f"Center: {center['longitude']}, {center['latitude']}")
```

### Stitch tiles together

```python
# See example script: stitch_tiles.py (coming soon)
```

## Troubleshooting

### Rate Limit Errors (429)

- Increase `RATE_LIMIT_DELAY` (e.g., to 1.0 or 2.0 seconds)
- Download in smaller batches

### Resolution Errors (400)

- Increase `TARGET_MPP` (lower resolution)
- Reduce `tile_size_px`

### Token Errors (401)

- Verify credentials in `.env`
- Check token hasn't expired (auto-refresh should handle this)

### No Data / Black Tiles

- Area may have high cloud coverage
- Adjust `maxCloudCoverage` in `download_tiles.py`
- Try different date range (modify evalscript)

## Advanced: Custom Date Range

Edit the `data` section in `download_tiles.py`:

```python
"data": [{
    "type": "sentinel-2-l2a",
    "dataFilter": {
        "maxCloudCoverage": 30,
        "timeRange": {
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-12-31T23:59:59Z"
        }
    }
}]
```

## License

This tool uses Sentinel Hub API and Sentinel-2 data from ESA Copernicus program.
