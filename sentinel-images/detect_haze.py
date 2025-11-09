"""
Haze detection pipeline using trained PyTorch model.
"""
import os
import sys
import yaml
import torch
import torch.nn as nn
import argparse
from pathlib import Path
from PIL import Image
import torchvision.transforms as transforms
from datetime import datetime

# Configuration
MODEL_PATH = "best_model.pth"
CLASS_NAMES = ['cloud', 'smoke', 'haze']

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


def load_model(model_path):
    """Load trained PyTorch model."""
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    checkpoint = torch.load(model_path, map_location='cpu')
    
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
    
    # Detect number of classes
    if 'fc.weight' in state_dict:
        num_classes = state_dict['fc.weight'].shape[0]
    else:
        num_classes = 3
    
    # Try loading as ResNet
    from torchvision.models import resnet18, resnet34, resnet50
    
    for model_fn in [resnet18, resnet34, resnet50]:
        try:
            model = model_fn(weights=None)
            model.fc = nn.Linear(model.fc.in_features, num_classes)
            model.load_state_dict(state_dict)
            model.eval()
            return model
        except:
            continue
    
    raise RuntimeError("Failed to load model")


def classify_tile(model, image_path):
    """Classify a single tile."""
    try:
        image = Image.open(image_path).convert('RGB')
        input_tensor = TRANSFORM(image).unsqueeze(0)
        
        with torch.no_grad():
            outputs = model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
            predicted_idx = torch.argmax(probabilities).item()
        
        predicted_class = CLASS_NAMES[predicted_idx]
        confidence = probabilities[predicted_idx].item()
        
        probs_dict = {
            class_name: prob.item() 
            for class_name, prob in zip(CLASS_NAMES, probabilities)
        }
        
        return predicted_class, probs_dict, confidence
    except Exception as e:
        print(f"  Error: {e}")
        return None, None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to manifest.yaml")
    args = parser.parse_args()
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        sys.exit(1)
    
    # Load manifest
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    tiles_dir = manifest_path.parent
    
    # Load model
    print("Loading model...")
    model = load_model(MODEL_PATH)
    
    # Process tiles
    print("Processing tiles...")
    results = []
    class_counts = {cls: 0 for cls in CLASS_NAMES}
    
    for tile_info in manifest["tiles"]:
        if tile_info["status"] != "success":
            continue
        
        tile_path = tiles_dir / tile_info["filename"]
        if not tile_path.exists():
            continue
        
        predicted_class, probs, confidence = classify_tile(model, tile_path)
        
        if predicted_class:
            results.append({
                "filename": tile_info["filename"],
                "tile_id": tile_info["tile_id"],
                "tile_index": tile_info["tile_index"],
                "center": tile_info["center"],
                "bbox": tile_info["bbox"],
                "prediction": {
                    "class": predicted_class,
                    "confidence": round(confidence, 4),
                    "probabilities": {k: round(v, 4) for k, v in probs.items()}
                }
            })
            class_counts[predicted_class] += 1
    
    # Save results
    output = {
        "metadata": {
            "model_path": MODEL_PATH,
            "detection_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_tiles_processed": len(results),
            "class_counts": class_counts
        },
        "tiles": results
    }
    
    output_path = tiles_dir / "detection_results.yaml"
    with open(output_path, "w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False)
    
    print(f"✓ Results saved: {output_path}")
    print(f"Haze tiles: {class_counts['haze']}/{len(results)}")


if __name__ == "__main__":
    main()