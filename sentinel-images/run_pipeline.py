"""
Master pipeline script - runs full haze detection workflow.
"""
import subprocess
import sys
from pathlib import Path

def run_step(script_name, description):
    """Run a pipeline step."""
    print("\n" + "=" * 70)
    print(f"STEP: {description}")
    print("=" * 70)
    
    result = subprocess.run([sys.executable, script_name])
    
    if result.returncode != 0:
        print(f"\n❌ Step failed: {description}")
        sys.exit(1)
    
    print(f"\n✓ Step completed: {description}")


def main():
    print("=" * 70)
    print("HAZE PREDICTION PIPELINE")
    print("=" * 70)
    print("\nThis will:")
    print("1. Download satellite tiles")
    print("2. Detect haze using trained model")
    print("3. Visualize results on a map")
    print()
    
    # Check if model exists
    if not Path("best_model.pth").exists():
        print("❌ best_model.pth not found in current directory")
        sys.exit(1)
    
    # Step 1: Download tiles (or use existing)
    if not Path("tiles_manifest.yaml").exists():
        response = input("Download tiles? This may take a while. (y/n): ")
        if response.lower() == 'y':
            run_step("download_tiles.py", "Download satellite tiles")
        else:
            print("Skipping download. Using existing tiles.")
    else:
        print("\n✓ Found existing tiles_manifest.yaml")
    
    # Step 2: Detect haze
    run_step("detect_haze.py", "Detect haze in tiles")
    
    # Step 3: Visualize
    run_step("visualize_haze.py", "Generate visualization map")
    
    print("\n" + "=" * 70)
    print("✓ PIPELINE COMPLETE!")
    print("=" * 70)
    print("\nOutput files:")
    print("  - tiles/              (Downloaded satellite images)")
    print("  - tiles_manifest.yaml (Tile metadata)")
    print("  - haze_detection_results.yaml (Classification results)")
    print("  - haze_map.png        (Visualization)")
    print("=" * 70)


if __name__ == "__main__":
    main()