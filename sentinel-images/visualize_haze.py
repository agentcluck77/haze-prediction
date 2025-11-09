"""
Visualize haze detection results on a map.
"""
import yaml
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np

RESULTS_PATH = "haze_detection_results.yaml"
OUTPUT_MAP = "haze_map.png"

# Color scheme for classes
CLASS_COLORS = {
    'cloud': (0.7, 0.7, 0.7, 0.6),  # Gray
    'smoke': (0.4, 0.4, 0.4, 0.7),   # Dark gray
    'haze': (1.0, 0.4, 0.4, 0.7)     # Red
}


def plot_haze_map(results):
    """Create a map showing classified tiles."""
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Get bbox extent
    meta = results["metadata"]
    tiles = results["tiles"]
    
    if not tiles:
        print("No tiles to plot")
        return
    
    # Find map extent from all tile bboxes
    all_bboxes = [t["bbox"] for t in tiles]
    min_lon = min(bbox[0] for bbox in all_bboxes)
    min_lat = min(bbox[1] for bbox in all_bboxes)
    max_lon = max(bbox[2] for bbox in all_bboxes)
    max_lat = max(bbox[3] for bbox in all_bboxes)
    
    # Set up map
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title('Haze Detection Results - SE Asia', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Plot tiles
    for tile in tiles:
        bbox = tile["bbox"]
        pred = tile["prediction"]
        class_name = pred["class"]
        confidence = pred["confidence"]
        
        # Get color for this class
        color = CLASS_COLORS.get(class_name, (0.5, 0.5, 0.5, 0.5))
        
        # Adjust alpha based on confidence
        color_with_conf = (*color[:3], color[3] * confidence)
        
        # Draw rectangle
        rect = Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            facecolor=color_with_conf,
            edgecolor=color[:3],
            linewidth=0.5
        )
        ax.add_patch(rect)
        
        # Optionally add text for high-confidence haze
        if class_name == 'haze' and confidence > 0.8:
            center = tile["center"]
            ax.text(center["longitude"], center["latitude"], 
                   f"{confidence:.0%}",
                   ha='center', va='center', fontsize=6,
                   color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', 
                           facecolor='red', alpha=0.7))
    
    # Create legend
    legend_patches = [
        mpatches.Patch(color=CLASS_COLORS[cls], label=f"{cls.capitalize()}")
        for cls in CLASS_COLORS.keys()
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=10)
    
    # Add statistics box
    class_counts = meta["class_counts"]
    total = meta["total_tiles_processed"]
    stats_text = f"Total tiles: {total}\n"
    for cls, count in class_counts.items():
        pct = (count / total * 100) if total else 0
        stats_text += f"{cls.capitalize()}: {count} ({pct:.1f}%)\n"
    
    ax.text(0.02, 0.98, stats_text,
           transform=ax.transAxes,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
           fontsize=9, family='monospace')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_MAP, dpi=300, bbox_inches='tight')
    print(f"✓ Map saved to: {OUTPUT_MAP}")


def print_summary(results):
    """Print text summary."""
    meta = results["metadata"]
    tiles = results["tiles"]
    
    print("=" * 70)
    print("HAZE DETECTION SUMMARY")
    print("=" * 70)
    print(f"Model: {meta['model_path']}")
    print(f"Detection timestamp: {meta['detection_timestamp']}")
    print(f"Total tiles: {meta['total_tiles_processed']}")
    print("\nClass distribution:")
    for cls, count in meta['class_counts'].items():
        pct = (count / meta['total_tiles_processed'] * 100) if meta['total_tiles_processed'] else 0
        print(f"  {cls:10s}: {count:4d} ({pct:5.1f}%)")
    
    # Find high-confidence haze tiles
    haze_tiles = [t for t in tiles if t['prediction']['class'] == 'haze']
    if haze_tiles:
        print(f"\nHigh-confidence haze regions ({len(haze_tiles)} tiles):")
        for tile in sorted(haze_tiles, key=lambda t: t['prediction']['confidence'], reverse=True)[:10]:
            center = tile['center']
            conf = tile['prediction']['confidence']
            print(f"  {tile['filename']:20s} | Lon: {center['longitude']:8.4f}, Lat: {center['latitude']:7.4f} | {conf:.1%}")
    
    print("=" * 70)


def main():
    # Load results
    if not Path(RESULTS_PATH).exists():
        print(f"❌ Results not found: {RESULTS_PATH}")
        print("Run detect_haze.py first")
        return
    
    with open(RESULTS_PATH) as f:
        results = yaml.safe_load(f)
    
    # Print summary
    print_summary(results)
    
    # Plot map
    print("\nGenerating map...")
    plot_haze_map(results)
    print("\n✓ Visualization complete!")


if __name__ == "__main__":
    main()