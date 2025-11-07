import os
import torch
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as transforms
import pandas as pd
import argparse
from pathlib import Path
import time
from transformers import ViTForImageClassification
import numpy as np

# Class mapping for HacX dataset (matches training encoding)
# Training uses LabelEncoder with sorted(['haze', 'normal', 'smoke'])
CLASS_MAPPING = ['haze', 'normal', 'smoke']  # 0=haze, 1=normal, 2=smoke

def get_transforms(image_size=384):
    """Get transforms for preprocessing."""
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

def load_model(model_path, device):
    """Load the trained model (detects architecture from checkpoint)."""
    # If directory, find the model file
    if os.path.isdir(model_path):
        model_files = [f for f in os.listdir(model_path) if f.endswith(('.pth', '.pt', '.pkl'))]
        if not model_files:
            raise FileNotFoundError(f"No model files found in {model_path}")
        model_path = os.path.join(model_path, model_files[0])
    
    print(f"Loading model from {model_path}")
    
    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    
    # Extract state dict
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
    
    # Detect model architecture from state dict keys
    if any('vit.' in key for key in state_dict.keys()):
        print("Detected ViT architecture")
        model = ViTForImageClassification.from_pretrained(
            'google/vit-base-patch16-384',
            num_labels=3,
            ignore_mismatched_sizes=True
        )
    elif any('convnext.' in key for key in state_dict.keys()):
        print("Detected ConvNeXt architecture")
        from transformers import ConvNextForImageClassification
        model = ConvNextForImageClassification.from_pretrained(
            'facebook/convnext-base-224-22k',
            num_labels=3,
            ignore_mismatched_sizes=True
        )
    else:
        print("Unknown architecture, defaulting to ViT")
        model = ViTForImageClassification.from_pretrained(
            'google/vit-base-patch16-384',
            num_labels=3,
            ignore_mismatched_sizes=True
        )
    
    # Load state dict
    model.load_state_dict(state_dict, strict=False)
    
    model.to(device)
    model.eval()
    
    print("Model loaded successfully")
    return model

def get_actual_class_from_filename(filename):
    """Extract actual class from filename based on naming convention (matches training encoding)."""
    filename_lower = filename.lower()

    # Match training encoding: 0=haze, 1=normal, 2=smoke
    # Check for haze
    if 'haze' in filename_lower:
        return 0  # haze
    # Check for smoke/wildfire
    elif 'smoke' in filename_lower or 'wildfire' in filename_lower:
        return 2  # smoke
    # Everything else is normal (cloud, land, seaside, dust)
    else:
        return 1  # normal

def process_image(image_path, transform, device):
    """Process a single image and return prediction."""
    try:
        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0).to(device)
        
        return image_tensor
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def run_inference(model, test_data_dir, output_file, device):
    """Run inference on all test images."""
    print(f"Running inference on images in {test_data_dir}")
    
    # Get transforms
    transform = get_transforms()
    
    # Find all .tif files
    test_files = list(Path(test_data_dir).glob('*.tif'))
    if not test_files:
        # Search recursively in subdirectories
        test_files = list(Path(test_data_dir).rglob('*.tif'))
    
    if not test_files:
        print(f"No .tif files found in {test_data_dir}")
        return
    
    print(f"Found {len(test_files)} test images")
    
    # Prepare results list
    results = []
    
    # Process each image
    for i, image_path in enumerate(test_files):
        filename = image_path.name
        
        # Process image
        image_tensor = process_image(image_path, transform, device)
        if image_tensor is None:
            continue
        
        # Run inference
        with torch.no_grad():
            outputs = model(pixel_values=image_tensor)
            logits = outputs.logits
            probabilities = F.softmax(logits, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
        
        # Get actual class from filename
        actual_class = get_actual_class_from_filename(filename)
        
        # Store result
        results.append({
            'file_name': filename,
            'predicted_class': predicted_class,
            'actual_class': actual_class
        })
        
        # Save results incrementally
        if i % 10 == 0 or i == len(test_files) - 1:
            df = pd.DataFrame(results)
            df.to_csv(output_file, index=False)
            print(f"Processed {i+1}/{len(test_files)} images")
    
    print(f"Inference complete. Results saved to {output_file}")
    return results

def main():
    parser = argparse.ArgumentParser(description='Run inference with ViT model')
    parser.add_argument('--model', type=str, default='/app/weights/best_model.pth',
                       help='Path to trained model weights directory or file')
    parser.add_argument('--test-data', type=str, default='/data/test',
                       help='Directory containing test images')
    parser.add_argument('--output', type=str, default='/data/output/predictions.csv',
                       help='Output CSV file for predictions')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Batch size for inference')
    
    args = parser.parse_args()
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Load model
    model = load_model(args.model, device)
    
    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Run inference
    start_time = time.time()
    results = run_inference(model, args.test_data, args.output, device)
    end_time = time.time()
    
    if results:
        print(f"\nProcessed {len(results)} images in {end_time - start_time:.2f} seconds")
        print(f"Average time per image: {(end_time - start_time) / len(results):.4f} seconds")
        
        # Calculate accuracy
        correct = sum(1 for r in results if r['predicted_class'] == r['actual_class'])
        accuracy = correct / len(results)
        print(f"Accuracy: {accuracy:.4f} ({correct}/{len(results)})")

if __name__ == '__main__':
    main()