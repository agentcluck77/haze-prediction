import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.cuda.amp import GradScaler, autocast
from transformers import (
    ViTForImageClassification, 
    ViTImageProcessor,
    ConvNextForImageClassification,
    ConvNextImageProcessor,
    get_scheduler
)
from tqdm import tqdm
import wandb
import argparse
import yaml
import copy
from dataset import create_dataloaders
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def compute_metrics(preds, labels):
    preds = np.argmax(preds, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    acc = accuracy_score(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }

def mixup_data(x, y, alpha=0.2):
    """Returns mixed inputs, pairs of targets, and lambda"""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1

    batch_size = x.size()[0]
    index = torch.randperm(batch_size)

    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam

def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)

class EMA:
    """Exponential Moving Average for model weights"""
    def __init__(self, model, decay=0.999):
        self.model = model
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        self.register()

    def register(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = (1.0 - self.decay) * param.data + self.decay * self.shadow[name]

    def apply_shadow(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data = self.shadow[name]

    def restore(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                param.data = self.backup[name]
        self.backup = {}

def get_loss_function(config):
    """Get loss function based on config"""
    loss_config = config.get('loss', {})
    loss_type = loss_config.get('type', 'cross_entropy')
    
    if loss_type == 'cross_entropy':
        if config['training']['label_smoothing'] > 0:
            return nn.CrossEntropyLoss(label_smoothing=config['training']['label_smoothing'])
        else:
            weights = loss_config.get('class_weights')
            if weights:
                weights = torch.tensor(weights)
            return nn.CrossEntropyLoss(weight=weights)
    
    elif loss_type == 'focal':
        class FocalLoss(nn.Module):
            def __init__(self, alpha=1.0, gamma=2.0, reduction='mean'):
                super(FocalLoss, self).__init__()
                self.alpha = alpha
                self.gamma = gamma
                self.reduction = reduction

            def forward(self, inputs, targets):
                ce_loss = F.cross_entropy(inputs, targets, reduction='none')
                pt = torch.exp(-ce_loss)
                focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
                if self.reduction == 'mean':
                    return focal_loss.mean()
                elif self.reduction == 'sum':
                    return focal_loss.sum()
                else:
                    return focal_loss
        
        return FocalLoss(
            alpha=loss_config.get('focal_alpha', 1.0),
            gamma=loss_config.get('focal_gamma', 2.0)
        )
    
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")

def train_model(model, train_loader, val_loader, optimizer, scheduler, num_epochs, device, save_dir, config):
    scaler = torch.amp.GradScaler('cuda')
    criterion = get_loss_function(config)
    
    # Initialize EMA if enabled
    ema = None
    if config['advanced']['use_ema']:
        ema = EMA(model, decay=config['advanced']['ema_decay'])
    
    best_val_acc = 0.0
    
    # Apply hardware optimizations
    if config['hardware']['use_tf32']:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    
    if config['hardware']['cudnn_benchmark']:
        torch.backends.cudnn.benchmark = True
    
    # Compile model if enabled (PyTorch 2.0+)
    if config['hardware']['compile_model']:
        try:
            model = torch.compile(model)
            print("Model compiled successfully")
        except:
            print("Model compilation failed, continuing without compilation")
    
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_preds = []
        train_labels = []
        
        train_pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Train]')
        for batch_idx, batch in enumerate(train_pbar):
            pixel_values = batch['pixel_values'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            
            # Apply MixUp if enabled
            if config['advanced']['use_mixup']:
                pixel_values, labels_a, labels_b, lam = mixup_data(
                    pixel_values, labels, config['advanced']['mixup_alpha']
                )
            else:
                labels_a = labels_b = labels
                lam = 1.0
            
            with torch.amp.autocast('cuda'):
                outputs = model(pixel_values=pixel_values)
                if config['advanced']['use_mixup']:
                    loss = mixup_criterion(criterion, outputs.logits, labels_a, labels_b, lam)
                else:
                    loss = criterion(outputs.logits, labels)
            
            # Gradient accumulation
            loss = loss / config['training']['gradient_accumulation_steps']
            scaler.scale(loss).backward()
            
            if (batch_idx + 1) % config['training']['gradient_accumulation_steps'] == 0:
                # Gradient clipping
                if config['training']['max_grad_norm'] > 0:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config['training']['max_grad_norm'])
                
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            
            # Update EMA
            if ema is not None:
                ema.update()
            
            train_loss += loss.item()
            train_preds.extend(outputs.logits.detach().cpu().numpy())
            train_labels.extend(labels.cpu().numpy())
            
            train_pbar.set_postfix({'loss': loss.item()})
        
        scheduler.step()
        
        # Calculate training metrics
        train_metrics = compute_metrics(np.array(train_preds), np.array(train_labels))
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_labels = []
        
        with torch.no_grad():
            # Use EMA model for validation if enabled
            if ema is not None:
                ema.apply_shadow()
            
            val_pbar = tqdm(val_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Val]')
            for batch in val_pbar:
                pixel_values = batch['pixel_values'].to(device)
                labels = batch['labels'].to(device)
                
                with torch.amp.autocast('cuda'):
                    outputs = model(pixel_values=pixel_values)
                    loss = criterion(outputs.logits, labels)
                
                val_loss += loss.item()
                val_preds.extend(outputs.logits.cpu().numpy())
                val_labels.extend(labels.cpu().numpy())
                
                val_pbar.set_postfix({'loss': loss.item()})
        
        # Restore original model weights if EMA was used
            if ema is not None:
                ema.restore()
        
        # Calculate validation metrics
        val_metrics = compute_metrics(np.array(val_preds), np.array(val_labels))
        
        # Log metrics
        wandb.log({
            'epoch': epoch + 1,
            'train_loss': train_loss / len(train_loader),
            'val_loss': val_loss / len(val_loader),
            'train_acc': train_metrics['accuracy'],
            'val_acc': val_metrics['accuracy'],
            'train_f1': train_metrics['f1'],
            'val_f1': val_metrics['f1'],
            'learning_rate': scheduler.get_last_lr()[0]
        })
        
        print(f'Epoch {epoch+1}/{num_epochs}:')
        print(f'  Train Loss: {train_loss/len(train_loader):.4f}, Acc: {train_metrics["accuracy"]:.4f}')
        print(f'  Val Loss: {val_loss/len(val_loader):.4f}, Acc: {val_metrics["accuracy"]:.4f}')
        
        # Save best model
        if val_metrics['accuracy'] > best_val_acc:
            best_val_acc = val_metrics['accuracy']
            
            # Save EMA model if enabled
            if ema is not None:
                ema.apply_shadow()
                model_state = model.state_dict()
                ema.restore()
            else:
                model_state = model.state_dict()
            
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model_state,
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'best_val_acc': best_val_acc,
                'config': config,
            }, os.path.join(save_dir, 'best_model.pth'))
            print(f'  New best model saved with val_acc: {best_val_acc:.4f}')
        
        # Save checkpoint every N epochs
        save_every = config['checkpointing']['save_every_n_epochs']
        if (epoch + 1) % save_every == 0:
            checkpoint_data = {
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'val_acc': val_metrics['accuracy'],
                'config': config,
            }
            
            # Save EMA state if enabled
            if ema is not None:
                checkpoint_data['ema_shadow'] = ema.shadow
            
            torch.save(checkpoint_data, os.path.join(save_dir, f'checkpoint_epoch_{epoch+1}.pth'))

def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def main():
    parser = argparse.ArgumentParser(description='Train ViT-B/16 on HacX dataset')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--data_dir', type=str, help='Override data directory')
    parser.add_argument('--batch_size', type=int, help='Override batch size')
    parser.add_argument('--num_epochs', type=int, help='Override number of epochs')
    parser.add_argument('--learning_rate', type=float, help='Override learning rate')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments if provided
    if args.data_dir:
        config['data']['train_dir'] = os.path.join(args.data_dir, 'train')
        config['data']['val_dir'] = os.path.join(args.data_dir, 'test')
    if args.batch_size:
        config['data']['batch_size'] = args.batch_size
    if args.num_epochs:
        config['training']['num_epochs'] = args.num_epochs
    if args.learning_rate:
        config['training']['learning_rate'] = args.learning_rate
    
    # Create unique save directory with timestamp
    base_save_dir = config['checkpointing']['save_dir']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_type = config['model'].get('type', 'vit').upper()
    run_name = f"{model_type}_{timestamp}"
    save_dir = os.path.join(base_save_dir, run_name)
    os.makedirs(save_dir, exist_ok=True)
    
    # Update config with actual save directory
    config['checkpointing']['save_dir'] = save_dir
    config['run_name'] = run_name
    
    print(f"Checkpoints will be saved to: {save_dir}")
    
    # Initialize wandb
    wandb.init(
        project=config['logging']['project_name'], 
        name=f"{config['logging']['run_name']}_{run_name}", 
        config=config
    )
    
    # Set device
    device = torch.device(config['hardware']['device'] if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    
    # Create dataloaders
    train_loader, val_loader, class_names = create_dataloaders(
        config['data']['train_dir'].replace('/train', ''), 
        batch_size=config['data']['batch_size'], 
        image_size=config['model']['image_size'],
        num_workers=config['data']['num_workers'],
        config=config
    )
    
    print(f'Classes: {class_names}')
    print(f'Train samples: {len(train_loader.dataset)}')
    print(f'Val samples: {len(val_loader.dataset)}')
    
    # Load model based on config
    model_type = config['model'].get('type', 'vit').lower()
    
    if model_type == 'vit':
        model = ViTForImageClassification.from_pretrained(
            config['model']['name'],
            num_labels=len(class_names),
            ignore_mismatched_sizes=True
        )
    elif model_type == 'convnext':
        model = ConvNextForImageClassification.from_pretrained(
            config['model']['name'],
            num_labels=len(class_names),
            ignore_mismatched_sizes=True
        )
    else:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: 'vit', 'convnext'")
    
    # Enable full fine-tuning (all parameters will be updated)
    for param in model.parameters():
        param.requires_grad = True
    
    model = model.to(device)
    
    # Print model info
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f'Total parameters: {total_params:,}')
    print(f'Trainable parameters: {trainable_params:,}')
    
    # Setup optimizer
    optimizer_config = config['optimizer']
    if optimizer_config['type'] == 'adamw':
        optimizer = torch.optim.AdamW(
            model.parameters(), 
            lr=float(config['training']['learning_rate']), 
            weight_decay=float(config['training']['weight_decay']),
            betas=tuple(optimizer_config['betas']),
            eps=float(optimizer_config['eps']),
            amsgrad=bool(optimizer_config['amsgrad'])
        )
    elif optimizer_config['type'] == 'adam':
        optimizer = torch.optim.Adam(
            model.parameters(), 
            lr=float(config['training']['learning_rate']), 
            weight_decay=float(config['training']['weight_decay']),
            betas=tuple(optimizer_config['betas']),
            eps=float(optimizer_config['eps']),
            amsgrad=bool(optimizer_config['amsgrad'])
        )
    elif optimizer_config['type'] == 'sgd':
        optimizer = torch.optim.SGD(
            model.parameters(), 
            lr=float(config['training']['learning_rate']), 
            weight_decay=float(config['training']['weight_decay']),
            momentum=float(optimizer_config.get('momentum', 0.9))
        )
    elif optimizer_config['type'] == 'rmsprop':
        optimizer = torch.optim.RMSprop(
            model.parameters(), 
            lr=float(config['training']['learning_rate']), 
            weight_decay=float(config['training']['weight_decay']),
            alpha=float(optimizer_config.get('alpha', 0.99)),
            eps=float(optimizer_config['eps'])
        )
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_config['type']}")
    
    num_training_steps = int(config['training']['num_epochs']) * len(train_loader)
    scheduler = get_scheduler(
        name=config['training']['scheduler'],
        optimizer=optimizer,
        num_warmup_steps=int(config['training']['warmup_steps']),
        num_training_steps=num_training_steps
    )
    
    # Train model
    train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        optimizer=optimizer,
        scheduler=scheduler,
        num_epochs=config['training']['num_epochs'],
        device=device,
        save_dir=config['checkpointing']['save_dir'],
        config=config
    )
    
    wandb.finish()

if __name__ == '__main__':
    main()