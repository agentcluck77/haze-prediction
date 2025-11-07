#!/usr/bin/env python3
"""
Convert folder-based image dataset to JSONL format for Azure AutoML.
Assumes folder structure: dataset/train/<class_name>/*.tif
                          dataset/test/<class_name>/*.tif
"""

import os
import json
from pathlib import Path
import argparse


def create_jsonl(data_dir, output_file):
    """
    Create JSONL file from folder structure.

    Args:
        data_dir: Path to directory containing class folders
        output_file: Path to output JSONL file
    """
    annotations = []

    data_path = Path(data_dir)

    # Iterate through class folders
    for class_folder in sorted(data_path.iterdir()):
        if not class_folder.is_dir():
            continue

        class_name = class_folder.name

        # Find all image files
        for image_file in sorted(class_folder.glob('*.tif')):
            # Create relative path from data_dir
            relative_path = str(image_file.relative_to(data_path.parent))

            annotation = {
                "image_url": relative_path,
                "label": class_name
            }
            annotations.append(annotation)

    # Write JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        for annotation in annotations:
            f.write(json.dumps(annotation) + '\n')

    print(f"Created {output_file} with {len(annotations)} images")

    # Print class distribution
    class_counts = {}
    for ann in annotations:
        label = ann['label']
        class_counts[label] = class_counts.get(label, 0) + 1

    print("\nClass distribution:")
    for class_name, count in sorted(class_counts.items()):
        print(f"  {class_name}: {count} images")


def main():
    parser = argparse.ArgumentParser(
        description='Convert folder-based dataset to JSONL for Azure AutoML'
    )
    parser.add_argument(
        '--train-dir',
        default='HacX-dataset/train',
        help='Path to training data directory'
    )
    parser.add_argument(
        '--test-dir',
        default='HacX-dataset/test',
        help='Path to test data directory'
    )

    args = parser.parse_args()

    # Create JSONL files
    create_jsonl(args.train_dir, f'{args.train_dir}/train_annotations.jsonl')
    create_jsonl(args.test_dir, f'{args.test_dir}/test_annotations.jsonl')


if __name__ == '__main__':
    main()
