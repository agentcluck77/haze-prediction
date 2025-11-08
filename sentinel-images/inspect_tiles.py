"""
Utility script to inspect and visualize downloaded tiles.
"""
import yaml
from pathlib import Path
import sys

def load_manifest(manifest_path="tiles_manifest.yaml"):
    """Load the tiles manifest."""
    if not Path(manifest_path).exists():
        print(f"❌ Manifest not found: {manifest_path}")
        print("Run download_tiles.py first")
        sys.exit(1)
    
    with open(manifest_path) as f:
        return yaml.safe_load(f)

def print_summary(manifest):
    """Print summary statistics."""
    meta = manifest["metadata"]
    tiles = manifest["tiles"]
    
    successful = sum(1 for t in tiles if t["status"] == "success")
    failed = sum(1 for t in tiles if t["status"] == "failed")
    
    print("=" * 70)
    print("TILES MANIFEST SUMMARY")
    print("=" * 70)
    print(f"Total tiles:          {meta['total_tiles']}")
    print(f"Successful downloads: {successful}")
    print(f"Failed downloads:     {failed}")
    print(f"Target resolution:    {meta['target_mpp']} m/px")
    print(f"Tile size:            {meta['tile_size_px']} x {meta['tile_size_px']} px")
    print(f"Full bbox:            {meta['bbox_full']}")
    print(f"Download timestamp:   {meta['download_timestamp']}")
    print("=" * 70)

def list_tiles(manifest, limit=10):
    """List first N tiles."""
    tiles = manifest["tiles"]
    print(f"\nFirst {min(limit, len(tiles))} tiles:")
    print("-" * 70)
    
    for tile in tiles[:limit]:
        status_icon = "✓" if tile["status"] == "success" else "✗"
        center = tile["center"]
        print(f"{status_icon} {tile['filename']:20s} | "
              f"Center: ({center['longitude']:9.4f}, {center['latitude']:8.4f}) | "
              f"Status: {tile['status']}")

def get_tile_by_coords(manifest, lon, lat):
    """Find the tile closest to given coordinates."""
    tiles = manifest["tiles"]
    
    best_tile = None
    best_dist = float('inf')
    
    for tile in tiles:
        center = tile["center"]
        dist = ((center["longitude"] - lon)**2 + (center["latitude"] - lat)**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_tile = tile
    
    return best_tile

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Inspect tiles manifest")
    parser.add_argument("--manifest", default="tiles_manifest.yaml", 
                       help="Path to manifest file")
    parser.add_argument("--list", type=int, default=10, 
                       help="Number of tiles to list")
    parser.add_argument("--find", nargs=2, type=float, metavar=("LON", "LAT"),
                       help="Find tile closest to coordinates")
    
    args = parser.parse_args()
    
    manifest = load_manifest(args.manifest)
    print_summary(manifest)
    
    if args.find:
        lon, lat = args.find
        tile = get_tile_by_coords(manifest, lon, lat)
        print(f"\nClosest tile to ({lon}, {lat}):")
        print(f"  File: {tile['filename']}")
        print(f"  Center: ({tile['center']['longitude']}, {tile['center']['latitude']})")
        print(f"  Bbox: {tile['bbox']}")
        print(f"  Status: {tile['status']}")
    else:
        list_tiles(manifest, args.list)
    
    print()

if __name__ == "__main__":
    main()
