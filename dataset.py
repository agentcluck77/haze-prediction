import os
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as transforms
from sklearn.preprocessing import LabelEncoder
import json

class HacXDataset(Dataset):
    def __init__(self, data_dir, split='train', transform=None):
        self.data_dir = data_dir
        self.split = split
        self.transform = transform
        
        # Load annotations
        annotations_file = os.path.join(data_dir, split, f'{split}_annotations.jsonl')
        self.samples = []
        
        with open(annotations_file, 'r') as f:
            for line in f:
                data = json.loads(line.strip())
                self.samples.append(data)
        
        # Extract unique classes and create label encoder
        # Use fixed class mapping: smoke=0, haze=1, normal=2 (matches inference script)
        self.classes = ['smoke', 'haze', 'normal']  # Fixed order to match inference
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(self.classes)
        
        # Verify all labels in dataset are in our fixed classes
        unique_labels = set([sample['label'] for sample in self.samples])
        if not unique_labels.issubset(set(self.classes)):
            raise ValueError(f"Found unexpected labels in dataset: {unique_labels - set(self.classes)}. Expected only: {self.classes}")
        
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load image
        img_path = os.path.join(self.data_dir, sample['image_url'])
        image = Image.open(img_path).convert('RGB')
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        # Encode label
        label = self.label_encoder.transform([sample['label']])[0]
        
        return {
            'pixel_values': image,
            'labels': torch.tensor(label, dtype=torch.long)
        }

def get_transforms(image_size=384, is_train=True, config=None):
    if config is None:
        # Default transforms if no config provided
        config = {
            'augmentation': {
                'horizontal_flip_prob': 0.5,
                'vertical_flip_prob': 0.0,
                'rotation_degrees': 10,
                'color_jitter': {'brightness': 0.2, 'contrast': 0.2, 'saturation': 0.2, 'hue': 0.1},
                'random_resized_crop': {'scale': [0.8, 1.0], 'ratio': [0.75, 1.33]},
                'gaussian_blur': {'enabled': False, 'kernel_size': 3, 'sigma': [0.1, 2.0]},
                'random_grayscale': 0.0,
                'gaussian_noise': {'enabled': False, 'mean': 0.0, 'std': 0.1},
                'solarization': {'enabled': False, 'threshold': 0.5}
            }
        }
    
    aug_config = config['augmentation']
    
    if is_train:
        transform_list = []
        
        # Add random resized crop if configured
        if aug_config['random_resized_crop']:
            transform_list.append(transforms.RandomResizedCrop(
                (image_size, image_size),
                scale=aug_config['random_resized_crop']['scale'],
                ratio=aug_config['random_resized_crop']['ratio']
            ))
        else:
            transform_list.append(transforms.Resize((image_size, image_size)))
        
        # Add flips
        if aug_config['horizontal_flip_prob'] > 0:
            transform_list.append(transforms.RandomHorizontalFlip(p=aug_config['horizontal_flip_prob']))
        if aug_config['vertical_flip_prob'] > 0:
            transform_list.append(transforms.RandomVerticalFlip(p=aug_config['vertical_flip_prob']))
        
        # Add rotation
        if aug_config['rotation_degrees'] > 0:
            transform_list.append(transforms.RandomRotation(degrees=aug_config['rotation_degrees']))
        
        # Add color jitter
        color_jitter = aug_config['color_jitter']
        if any(color_jitter.values()):
            transform_list.append(transforms.ColorJitter(
                brightness=color_jitter['brightness'],
                contrast=color_jitter['contrast'],
                saturation=color_jitter['saturation'],
                hue=color_jitter['hue']
            ))
        
        # Add gaussian blur
        if aug_config['gaussian_blur']['enabled']:
            transform_list.append(transforms.GaussianBlur(
                kernel_size=aug_config['gaussian_blur']['kernel_size'],
                sigma=aug_config['gaussian_blur']['sigma']
            ))
        
        # Add random grayscale
        if aug_config['random_grayscale'] > 0:
            transform_list.append(transforms.RandomGrayscale(p=aug_config['random_grayscale']))
        
        # Add solarization
        if aug_config['solarization']['enabled']:
            transform_list.append(transforms.RandomSolarization(
                threshold=aug_config['solarization']['threshold']
            ))
        
        # Convert to tensor and normalize
        transform_list.extend([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Add gaussian noise (custom transform)
        if aug_config['gaussian_noise']['enabled']:
            class GaussianNoise:
                def __init__(self, mean=0.0, std=0.1):
                    self.mean = mean
                    self.std = std
                
                def __call__(self, tensor):
                    noise = torch.randn(tensor.size()) * self.std + self.mean
                    return tensor + noise
            
            transform_list.append(GaussianNoise(
                mean=aug_config['gaussian_noise']['mean'],
                std=aug_config['gaussian_noise']['std']
            ))
        
        return transforms.Compose(transform_list)
    else:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

def create_dataloaders(data_dir, batch_size=16, image_size=384, num_workers=4, config=None):
    train_transform = get_transforms(image_size, is_train=True, config=config)
    val_transform = get_transforms(image_size, is_train=False, config=config)
    
    train_dataset = HacXDataset(data_dir, split='train', transform=train_transform)
    val_dataset = HacXDataset(data_dir, split='test', transform=val_transform)
    
    pin_memory = config['hardware']['pin_memory'] if config else True
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=num_workers,
        pin_memory=pin_memory
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers,
        pin_memory=pin_memory
    )
    
    return train_loader, val_loader, train_dataset.classes