"""
Analyze haze motion over time from time-series database.
Prepares data for wind-based prediction (future integration).
"""
import json
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

TIME_SERIES_DB = Path("time_series.json")


def load_time_series():
    """Load time series data."""
    if not TIME_SERIES_DB.exists():
        print("❌ No time series data found")
        return None
    
    with open(TIME_SERIES_DB) as f:
        return json.load(f)


def match_tiles_between_snapshots(snap1, snap2, max_distance_degrees=1.0):
    """Match haze tiles between two time snapshots by proximity."""
    matches = []
    
    haze1 = snap1["haze_tiles"]
    haze2 = snap2["haze_tiles"]
    
    for tile1 in haze1:
        center1 = np.array([tile1["center"]["longitude"], tile1["center"]["latitude"]])
        
        best_match = None
        min_dist = max_distance_degrees
        
        for tile2 in haze2:
            center2 = np.array([tile2["center"]["longitude"], tile2["center"]["latitude"]])
            dist = np.linalg.norm(center2 - center1)
            
            if dist < min_dist:
                min_dist = dist
                best_match = tile2
        
        if best_match:
            matches.append({
                "tile1": tile1,
                "tile2": best_match,
                "displacement": {
                    "lon": best_match["center"]["longitude"] - tile1["center"]["longitude"],
                    "lat": best_match["center"]["latitude"] - tile1["center"]["latitude"]
                },
                "distance_degrees": float(min_dist),
                "time_delta_hours": (
                    datetime.fromisoformat(snap2["timestamp"].replace("Z", "")) -
                    datetime.fromisoformat(snap1["timestamp"].replace("Z", ""))
                ).total_seconds() / 3600.0
            })
    
    return matches


def analyze_motion(time_series):
    """Analyze haze motion patterns."""
    snapshots = time_series["snapshots"]
    
    if len(snapshots) < 2:
        print("Need at least 2 snapshots for motion analysis")
        return None
    
    print(f"Analyzing {len(snapshots)} snapshots...")
    
    all_motions = []
    
    for i in range(len(snapshots) - 1):
        matches = match_tiles_between_snapshots(snapshots[i], snapshots[i+1])
        all_motions.extend(matches)
        print(f"  {snapshots[i]['timestamp']} → {snapshots[i+1]['timestamp']}: {len(matches)} matches")
    
    if not all_motions:
        print("No motion detected")
        return None
    
    # Compute statistics
    displacements = np.array([[m["displacement"]["lon"], m["displacement"]["lat"]] 
                             for m in all_motions])
    
    mean_displacement = displacements.mean(axis=0)
    std_displacement = displacements.std(axis=0)
    
    results = {
        "total_motion_vectors": len(all_motions),
        "mean_displacement": {
            "lon": float(mean_displacement[0]),
            "lat": float(mean_displacement[1])
        },
        "std_displacement": {
            "lon": float(std_displacement[0]),
            "lat": float(std_displacement[1])
        },
        "motion_vectors": all_motions
    }
    
    return results


def visualize_motion(motion_data):
    """Visualize motion vectors."""
    if not motion_data or not motion_data["motion_vectors"]:
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Motion vectors on map
    for mv in motion_data["motion_vectors"]:
        t1 = mv["tile1"]
        lon1, lat1 = t1["center"]["longitude"], t1["center"]["latitude"]
        dlon, dlat = mv["displacement"]["lon"], mv["displacement"]["lat"]
        
        ax1.arrow(lon1, lat1, dlon, dlat, 
                 head_width=0.1, head_length=0.1, 
                 fc='blue', ec='blue', alpha=0.5)
    
    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")
    ax1.set_title("Haze Motion Vectors")
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Displacement histogram
    displacements = np.array([[m["displacement"]["lon"], m["displacement"]["lat"]] 
                             for m in motion_data["motion_vectors"]])
    magnitudes = np.linalg.norm(displacements, axis=1)
    
    ax2.hist(magnitudes, bins=20, alpha=0.7, edgecolor='black')
    ax2.set_xlabel("Displacement (degrees)")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Motion Magnitude Distribution")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("motion_analysis.png", dpi=300, bbox_inches='tight')
    print("✓ Motion visualization saved: motion_analysis.png")


def main():
    print("=" * 70)
    print("Haze Motion Analysis")
    print("=" * 70)
    
    time_series = load_time_series()
    if not time_series:
        return
    
    print(f"Total snapshots: {len(time_series['snapshots'])}")
    
    motion_data = analyze_motion(time_series)
    
    if motion_data:
        print("\nMotion Statistics:")
        print(f"  Total vectors: {motion_data['total_motion_vectors']}")
        print(f"  Mean displacement (lon): {motion_data['mean_displacement']['lon']:.4f}°")
        print(f"  Mean displacement (lat): {motion_data['mean_displacement']['lat']:.4f}°")
        
        # Save results
        with open("motion_analysis.yaml", "w") as f:
            yaml.dump(motion_data, f, default_flow_style=False)
        
        print("\n✓ Motion analysis saved: motion_analysis.yaml")
        
        # Visualize
        visualize_motion(motion_data)


if __name__ == "__main__":
    main()