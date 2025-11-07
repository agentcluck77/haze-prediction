import torch
import gc
from dataset import create_dataloaders

def test_gpu_memory():
    """Test GPU memory and setup"""
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"PyTorch Version: {torch.__version__}")
    else:
        print("CUDA not available")

def test_data_loading():
    """Test data loading with different batch sizes"""
    try:
        print("\nTesting data loading...")
        
        # Test with batch size 8 (default for 384x384 images)
        train_loader, val_loader, class_names = create_dataloaders(
            'HacX-dataset', 
            batch_size=8, 
            image_size=384,
            num_workers=2
        )
        
        print(f"Classes: {class_names}")
        print(f"Train batches: {len(train_loader)}")
        print(f"Val batches: {len(val_loader)}")
        
        # Test one batch
        batch = next(iter(train_loader))
        print(f"Batch shape: {batch['pixel_values'].shape}")
        print(f"Batch labels: {batch['labels'].shape}")
        
        # Test memory usage
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            batch['pixel_values'] = batch['pixel_values'].cuda()
            batch['labels'] = batch['labels'].cuda()
            
            print(f"GPU memory after loading batch: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
            print(f"GPU memory reserved: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
            
            del batch['pixel_values'], batch['labels']
            torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        print(f"Error in data loading: {e}")
        return False

def test_model_loading():
    """Test ViT model loading and memory requirements"""
    try:
        print("\nTesting model loading...")
        
        from transformers import ViTForImageClassification
        
        # Load model
        model = ViTForImageClassification.from_pretrained(
            'google/vit-base-patch16-384',
            num_labels=3,
            ignore_mismatched_sizes=True
        )
        
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            model = model.cuda()
            
            print(f"GPU memory after loading model: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
            print(f"GPU memory reserved: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
        
        return True
        
    except Exception as e:
        print(f"Error in model loading: {e}")
        return False

def find_optimal_batch_size():
    """Find optimal batch size for GTX 4090"""
    print("\nFinding optimal batch size...")
    
    from transformers import ViTForImageClassification
    import torch.nn as nn
    
    model = ViTForImageClassification.from_pretrained(
        'google/vit-base-patch16-384',
        num_labels=3,
        ignore_mismatched_sizes=True
    )
    
    if torch.cuda.is_available():
        model = model.cuda()
        criterion = nn.CrossEntropyLoss()
        
        batch_sizes = [4, 8, 12, 16, 20, 24]
        
        for batch_size in batch_sizes:
            try:
                torch.cuda.empty_cache()
                
                # Create dummy input
                dummy_input = torch.randn(batch_size, 3, 384, 384).cuda()
                dummy_labels = torch.randint(0, 3, (batch_size,)).cuda()
                
                # Forward pass
                with torch.cuda.amp.autocast():
                    outputs = model(pixel_values=dummy_input, labels=dummy_labels)
                    loss = outputs.loss
                
                # Backward pass
                loss.backward()
                
                memory_used = torch.cuda.memory_allocated() / 1e9
                print(f"Batch size {batch_size}: {memory_used:.2f} GB used")
                
                if memory_used > 20:  # Leave some buffer
                    print(f"Batch size {batch_size} too large, stopping")
                    break
                    
            except RuntimeError as e:
                if "out of memory" in str(e):
                    print(f"Batch size {batch_size}: OOM")
                    break
                else:
                    print(f"Batch size {batch_size}: Error - {e}")
        
        torch.cuda.empty_cache()

if __name__ == '__main__':
    print("=== HacX ViT Training Setup Test ===")
    
    test_gpu_memory()
    
    if test_data_loading() and test_model_loading():
        find_optimal_batch_size()
        print("\n✅ Setup test completed successfully!")
    else:
        print("\n❌ Setup test failed!")