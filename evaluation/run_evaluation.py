#!/usr/bin/env python
"""Run model evaluation on test data."""

import torch
import pandas as pd
import os
import json
import argparse
from transformers import (
    ViTForImageClassification,
    ConvNextForImageClassification
)
from PIL import Image
import torchvision.transforms as transforms
from sklearn.preprocessing import LabelEncoder


def main():
    parser = argparse.ArgumentParser(description='Evaluate trained model on test data')
    parser.add_argument('--model_path', type=str, required=True, 
                        help='Path to model checkpoint file')
    parser.add_argument('--model_type', type=str, choices=['vit', 'convnext'], 
                        default='vit', help='Model architecture type')
    args = parser.parse_args()
    
    # Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    print(f"Loading {args.model_type.upper()} model from: {args.model_path}")
    
    # Load checkpoint first to determine model format
    checkpoint = torch.load(args.model_path, map_location=device)
    
    # Check if this is a training checkpoint or a HuggingFace model
    if 'model_state_dict' in checkpoint:
        # Training checkpoint format
        model_state = checkpoint['model_state_dict']
        config = checkpoint.get('config', {})
        
        # Initialize model based on config or args
        model_type = config.get('model', {}).get('type', args.model_type).lower()
        
        if model_type == 'vit':
            model = ViTForImageClassification.from_pretrained(
                config.get('model', {}).get('name', 'google/vit-base-patch16-384'), 
                num_labels=3, 
                ignore_mismatched_sizes=True
            )
            image_size = config.get('model', {}).get('image_size', 384)
        elif model_type == 'convnext':
            model = ConvNextForImageClassification.from_pretrained(
                config.get('model', {}).get('name', 'facebook/convnext-base-224'),
                num_labels=3,
                ignore_mismatched_sizes=True
            )
            image_size = config.get('model', {}).get('image_size', 224)
        
        model.load_state_dict(model_state)
        
    else:
        # Check if it's a raw state dict file
        if args.model_path.endswith('.bin') or args.model_path.endswith('.pth'):
            # Load raw state dict
            if args.model_type == 'vit':
                model = ViTForImageClassification.from_pretrained(
                    'google/vit-base-patch16-384', 
                    num_labels=3, 
                    ignore_mismatched_sizes=True
                )
                image_size = 384
            elif args.model_type == 'convnext':
                model = ConvNextForImageClassification.from_pretrained(
                    'facebook/convnext-base-224',
                    num_labels=3,
                    ignore_mismatched_sizes=True
                )
                image_size = 224
            
            # Load the state dict
            state_dict = torch.load(args.model_path, map_location=device)
            model.load_state_dict(state_dict, strict=False)  # strict=False allows missing keys
        else:
            # Direct HuggingFace model format
            if args.model_type == 'vit':
                model = ViTForImageClassification.from_pretrained(args.model_path, local_files_only=True)
                image_size = 384
            elif args.model_type == 'convnext':
                model = ConvNextForImageClassification.from_pretrained(args.model_path, local_files_only=True)
                image_size = 224
    
    model.to(device).eval()
    
    # Load test annotations
    test_annotations = {}
    annotations_file = '../HacX-dataset/test/test_annotations.jsonl'
    with open(annotations_file, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            filename = data['image_url'].split('/')[-1]  # Get just the filename
            test_annotations[filename] = data['label']
    
    # Create label encoder matching training
    classes = ['haze', 'normal', 'smoke']
    label_encoder = LabelEncoder()
    label_encoder.fit(classes)
    
    # Process test images - use appropriate transforms for model type
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    results = []
    
    # Find all test images
    for root, _, files in os.walk('test_data'):
        for file in files:
            if file.endswith('.tif') and file in test_annotations:
                img_path = os.path.join(root, file)
                
                # Get actual label from annotations
                actual_label = test_annotations[file]
                actual_class = label_encoder.transform([actual_label])[0]
                
                # Process image
                img = Image.open(img_path).convert('RGB')
                with torch.no_grad():
                    pred = torch.argmax(
                        model(pixel_values=transform(img).unsqueeze(0).to(device)).logits
                    ).item()
                
                results.append({
                    'file_name': file, 
                    'predicted_class': pred, 
                    'actual_class': actual_class
                })
    
    print(f"Processing {len(results)} test images...")
    
    # Save results
    os.makedirs('output', exist_ok=True)
    
    # Add model info to results
    for result in results:
        result['model_type'] = args.model_type
        result['model_path'] = args.model_path
    
    pd.DataFrame(results).to_csv('output/predictions.csv', index=False)
    
    # Calculate accuracy
    correct = sum(1 for r in results if r['predicted_class'] == r['actual_class'])
    accuracy = correct / len(results)
    print(f'Model: {args.model_type.upper()}')
    print(f'Accuracy: {accuracy:.4f} ({correct}/{len(results)})')
    print(f'Results saved to: output/predictions.csv')


if __name__ == '__main__':
    main()