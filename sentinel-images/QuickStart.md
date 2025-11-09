# Haze Detection Pipeline - Quick Start

## Prerequisites

1. **Set environment variables in `.env`:**

   ```bash
   SENTINELHUB_CLIENT_ID=your-client-id
   SENTINELHUB_CLIENT_SECRET=your-client-secret
   ```

2. **Ensure `best_model.pth` is in this directory**

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start (Automated Hourly Polling)

**Run the automated scheduler:**

```bash
python scheduler.py
```

This will:

- Run immediately on start
- Poll satellite data every 60 minutes
- Download tiles at optimal resolution (60m/px, ~400 tiles)
- Classify each tile as cloud/smoke/haze
- Generate visualization maps
- Track haze positions over time in `time_series.json`

**Stop scheduler:** Press `Ctrl+C`

## Manual Pipeline Run

**Run complete pipeline once:**

```bash
python run_pipeline.py
```

**Or run individual steps:**

```bash
# Step 1: Download tiles for current time
python download_tiles.py

# Step 2: Classify tiles (requires manifest path)
python detect_haze.py --manifest tiles/20241109_120000/manifest.yaml

# Step 3: Visualize results
python visualize_haze.py --manifest tiles/20241109_120000/manifest.yaml

# Step 4: Analyze motion (needs 2+ snapshots)
python analyze_motion.py
```

## Output Structure

```
sentinel-images/
├── tiles/
│   ├── 20241109_120000/              # Timestamp folder
│   │   ├── tile_a1b2c3.png           # Individual tile images
│   │   ├── manifest.yaml             # Tile coordinates & metadata
│   │   ├── detection_results.yaml   # ML predictions per tile
│   │   └── haze_map.png              # Visualization
│   ├── 20241109_130000/              # Next hourly run
│   │   └── ...
├── time_series.json                   # Historical haze positions
├── motion_analysis.yaml               # Motion vectors (after 2+ runs)
├── motion_analysis.png                # Motion visualization
└── best_model.pth                     # Your trained model
```

## Key Files

- **`time_series.json`** - All haze detections with timestamps and coordinates
- **`tiles/{timestamp}/manifest.yaml`** - Tile grid coordinates (for wind integration)
- **`motion_analysis.yaml`** - Computed haze movement vectors

## Configuration

### Download Resolution & Coverage

Edit `download_tiles.py`:

```python
TARGET_MPP = 60.0  # Resolution in meters per pixel
                   # 10  = highest quality, ~2500 tiles (slow)
                   # 60  = balanced, ~400 tiles (recommended)
                   # 100 = faster, ~144 tiles

BBOX_FULL = [95.038077, -6.419254, 117.950162, 4.370021]  # SE Asia region
```

### Polling Frequency

Edit `scheduler.py`:

```python
POLL_INTERVAL_MINUTES = 60  # Run every 60 minutes (adjustable)
```

### Model Configuration

Edit `detect_haze.py`:

```python
CLASS_NAMES = ['cloud', 'smoke', 'haze']  # Match your model's classes

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),  # Match your model's input size
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],  # Match training normalization
        std=[0.229, 0.224, 0.225]
    )
])
```

## Troubleshooting

### Rate Limiting (429 errors)

- System automatically retries with exponential backoff
- Reduce `TARGET_MPP` to decrease tile count
- Increase `MIN_REQUEST_INTERVAL` in `download_tiles.py`

### No haze detected

- Check `detection_results.yaml` for classification confidence
- Adjust cloud coverage filter in `download_tiles.py`:
  ```python
  "maxCloudCoverage": 30  # Increase to 50 or 70
  ```

### Model loading errors

If you used a custom architecture (not ResNet), modify `detect_haze.py`:

```python
# Add your model class definition
class YourCustomModel(nn.Module):
    def __init__(self):
        # ...

    def forward(self, x):
        # ...

# In load_model():
model = YourCustomModel()
model.load_state_dict(state_dict)
```

### Time zone issues

All timestamps are in UTC. The scheduler uses:

```python
datetime.utcnow()  # UTC timestamps
```

## Advanced Usage

### Query time series data

```python
import json
with open("time_series.json") as f:
    data = json.load(f)

# Get latest snapshot
latest = data["snapshots"][-1]
print(f"Haze tiles: {latest['haze_count']}")

# Get all haze positions over time
for snap in data["snapshots"]:
    print(f"{snap['timestamp']}: {snap['haze_count']} haze tiles")
```

### Find tiles by coordinates

```python
import yaml
with open("tiles/20241109_120000/manifest.yaml") as f:
    manifest = yaml.safe_load(f)

# Find tile containing Singapore (103.8, 1.35)
for tile in manifest["tiles"]:
    bbox = tile["bbox"]
    if bbox[0] <= 103.8 <= bbox[2] and bbox[1] <= 1.35 <= bbox[3]:
        print(f"Found: {tile['filename']}")
```

### Export for wind integration

Each tile has stable `tile_id` and coordinates:

```yaml
# tiles/20241109_120000/detection_results.yaml
tiles:
  - tile_id: "a1b2c3d4e5f6" # Stable across time
    center:
      longitude: 103.8
      latitude: 1.35
    bbox: [103.5, 1.0, 104.1, 1.7]
    prediction:
      class: "haze"
      confidence: 0.87
```

Use `tile_id` to match positions across timestamps for wind-based motion prediction.

## Next Steps

1. **Let scheduler run for 2-3 hours** to collect multiple snapshots
2. **Run motion analysis:** `python analyze_motion.py`
3. **Integrate wind data** (future):
   - Use `motion_analysis.yaml` displacement vectors
   - Correlate with wind speed/direction from weather API
   - Predict future haze positions

## Support

Check logs in scheduler output for detailed error messages.

Example healthy run:

```
[1/3] Downloading satellite tiles...
✓ Download complete
[2/3] Running haze detection...
✓ Detection complete (45 haze tiles)
[3/3] Updating time series database...
✓ Time series updated
```
