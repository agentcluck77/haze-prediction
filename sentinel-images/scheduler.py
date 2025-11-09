"""
Automated scheduler - polls satellite data every hour and runs inference.
Maintains time-series database for motion tracking.
"""
import os
import time
import yaml
import schedule
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys
import json

# Configuration
POLL_INTERVAL_MINUTES = 60  # Poll every hour
TIME_SERIES_DB = Path("time_series.json")
BBOX_FULL = [95.038077, -6.419254, 117.950162, 4.370021]

def load_time_series():
    """Load historical time series data."""
    if TIME_SERIES_DB.exists():
        with open(TIME_SERIES_DB) as f:
            return json.load(f)
    return {"snapshots": []}


def save_time_series(data):
    """Save time series data."""
    with open(TIME_SERIES_DB, "w") as f:
        json.dump(data, f, indent=2)


def run_pipeline():
    """Run full pipeline: download → detect → store results."""
    print("\n" + "=" * 80)
    print(f"SCHEDULED RUN: {datetime.utcnow().isoformat()}Z")
    print("=" * 80)
    
    try:
        # Step 1: Download tiles
        print("\n[1/3] Downloading satellite tiles...")
        result = subprocess.run([sys.executable, "download_tiles.py"], 
                              capture_output=True, text=True, timeout=3600)
        
        if result.returncode != 0:
            print(f"❌ Download failed: {result.stderr}")
            return False
        
        print("✓ Download complete")
        
        # Find the latest manifest
        tiles_dir = Path("tiles")
        manifests = sorted(tiles_dir.glob("*/manifest.yaml"), reverse=True)
        
        if not manifests:
            print("❌ No manifest found")
            return False
        
        latest_manifest = manifests[0]
        timestamp_dir = latest_manifest.parent
        
        # Step 2: Run inference
        print("\n[2/3] Running haze detection...")
        result = subprocess.run([sys.executable, "detect_haze.py", 
                               "--manifest", str(latest_manifest)],
                              capture_output=True, text=True, timeout=1800)
        
        if result.returncode != 0:
            print(f"❌ Detection failed: {result.stderr}")
            return False
        
        print("✓ Detection complete")
        
        # Step 3: Update time series database
        print("\n[3/3] Updating time series database...")
        
        with open(latest_manifest) as f:
            manifest = yaml.safe_load(f)
        
        detection_results_path = timestamp_dir / "detection_results.yaml"
        
        if detection_results_path.exists():
            with open(detection_results_path) as f:
                detection = yaml.safe_load(f)
            
            # Extract haze tiles
            haze_tiles = [
                {
                    "tile_id": t["tile_id"],
                    "center": t["center"],
                    "bbox": t["bbox"],
                    "confidence": t["prediction"]["confidence"],
                    "class": t["prediction"]["class"]
                }
                for t in detection["tiles"]
                if t["prediction"]["class"] == "haze" and t["prediction"]["confidence"] > 0.5
            ]
            
            # Add to time series
            time_series = load_time_series()
            time_series["snapshots"].append({
                "timestamp": manifest["metadata"]["timestamp"],
                "time_range": manifest["metadata"]["time_range"],
                "total_tiles": manifest["metadata"]["total_tiles"],
                "haze_tiles": haze_tiles,
                "haze_count": len(haze_tiles)
            })
            
            save_time_series(time_series)
            
            print(f"✓ Time series updated ({len(haze_tiles)} haze tiles)")
        
        # Step 4: Generate visualization
        print("\n[4/4] Generating visualization...")
        result = subprocess.run([sys.executable, "visualize_haze.py",
                               "--manifest", str(latest_manifest)],
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✓ Visualization complete")
        
        print("\n" + "=" * 80)
        print("✓ PIPELINE COMPLETE")
        print("=" * 80)
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Pipeline timeout")
        return False
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False


def check_system():
    """Check if system is ready."""
    print("Checking system...")
    
    # Check credentials
    if not os.environ.get("SENTINELHUB_CLIENT_ID"):
        print("❌ SENTINELHUB_CLIENT_ID not set")
        return False
    
    if not os.environ.get("SENTINELHUB_CLIENT_SECRET"):
        print("❌ SENTINELHUB_CLIENT_SECRET not set")
        return False
    
    # Check model
    if not Path("best_model.pth").exists():
        print("❌ best_model.pth not found")
        return False
    
    print("✓ System ready")
    return True


def main():
    """Main scheduler loop."""
    print("=" * 80)
    print("HAZE PREDICTION AUTOMATED SCHEDULER")
    print("=" * 80)
    print(f"Poll interval: {POLL_INTERVAL_MINUTES} minutes")
    print(f"Region: {BBOX_FULL}")
    print(f"Time series DB: {TIME_SERIES_DB}")
    print("=" * 80)
    
    if not check_system():
        print("\n❌ System check failed. Exiting.")
        sys.exit(1)
    
    # Schedule job
    schedule.every(POLL_INTERVAL_MINUTES).minutes.do(run_pipeline)
    
    # Run immediately on start
    print("\nRunning initial pipeline...")
    run_pipeline()
    
    # Enter scheduler loop
    print("\n✓ Scheduler started. Press Ctrl+C to stop.")
    print(f"Next run at: {datetime.now() + timedelta(minutes=POLL_INTERVAL_MINUTES)}")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\n✓ Scheduler stopped")


if __name__ == "__main__":
    main()