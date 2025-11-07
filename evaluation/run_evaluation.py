#!/usr/bin/env python
"""Run model evaluation on test data."""

import torch
import pandas as pd
import os
import json
from transformers import ViTForImageClassification
from PIL import Image
import torchvision.transforms as transforms
from sklearn.preprocessing import LabelEncoder


def main():
    # Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    model = ViTForImageClassification.from_pretrained(
        'google/vit-base-patch16-384', 
        num_labels=3, 
        ignore_mismatched_sizes=True
    )
    
    checkpoint = torch.load('weights/vit_b16_hacx.pth', map_location=device)
    model.load_state_dict(
        checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint
    )
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
    
    # Process test images
    transform = transforms.Compose([
        transforms.Resize((384, 384)),
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
    pd.DataFrame(results).to_csv('output/predictions.csv', index=False)
    
    # Calculate accuracy
    correct = sum(1 for r in results if r['predicted_class'] == r['actual_class'])
    accuracy = correct / len(results)
    print(f'Accuracy: {accuracy:.4f} ({correct}/{len(results)})')


if __name__ == '__main__':
    main()