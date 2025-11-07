# HacX Model Training

Training vision transformer and ConvNeXt models on HacX dataset with full fine-tuning.

## Setup

1. Install dependencies with uv:
```bash
uv sync
```

2. Test your setup:
```bash
uv run python test_setup.py
```

## Dataset

The HacX dataset should be in `HacX-dataset/` with the following structure:
```
HacX-dataset/
├── train/
│   ├── train_annotations.jsonl
│   ├── haze/
│   ├── normal/
│   └── smoke/
└── test/
    ├── test_annotations.jsonl
    ├── haze/
    ├── normal/
    └── smoke/
```

## Training

### Training Different Models

The training script now supports multiple model architectures through configuration files:

#### ViT Model (default)
```bash
uv run python train_vit.py --config config.yaml
```

#### ConvNeXt Model
```bash
uv run python train_vit.py --config config_convnext.yaml
```

### Custom Training Parameters

```bash
uv run python train_vit.py --config config.yaml \
  --batch_size 8 \
  --num_epochs 50 \
  --learning_rate 3e-5 \
  --data_dir HacX-dataset
```

### Parameters

- `--config`: Path to config file (default: config.yaml)
- `--batch_size`: Override batch size from config
- `--num_epochs`: Override number of epochs from config
- `--learning_rate`: Override learning rate from config
- `--data_dir`: Override dataset path from config

### Configuration Files

- `config.yaml`: ViT-B/16 configuration (384x384 input)
- `config_convnext.yaml`: ConvNeXt-Base configuration (224x224 input)

Each config file specifies:
- Model type and architecture
- Training hyperparameters
- Data augmentation settings
- Hardware optimizations

## Model Details

### Supported Architectures

#### ViT-B/16
- **Input**: 384x384
- **Parameters**: ~86M
- **Config**: `config.yaml`

#### ConvNeXt-Base
- **Input**: 224x224
- **Parameters**: ~88M
- **Config**: `config_convnext.yaml`

### Common Training Features
- **Training**: Full fine-tuning (all parameters updated)
- **Classes**: 3 (haze, normal, smoke)
- **Optimization**: AdamW with cosine scheduler
- **Mixed Precision**: Enabled for GTX 4090 optimization
- **Advanced Features**: EMA, MixUp, gradient accumulation, label smoothing

## Monitoring

Training progress is logged to Weights & Biases. Set your `WANDB_API_KEY` environment variable to enable logging.

## Checkpoints

Each training run creates a unique checkpoint folder:
- ViT: `checkpoints/VIT_YYYYMMDD_HHMMSS/`
- ConvNeXt: `checkpoints/CONVNEXT_YYYYMMDD_HHMMSS/`

Inside each folder:
- `best_model.pth`: Best validation model
- `checkpoint_epoch_N.pth`: Regular checkpoints (every 5 epochs)
- Config and training metadata included

## Model Evaluation

After training, evaluate your model using the evaluation system:

### Quick Evaluation

```bash
# Find your latest checkpoint (example for ViT)
LATEST_CHECKPOINT=$(ls -t checkpoints/VIT_* | head -n 1)

# Run evaluation for ViT model
cd evaluation
uv run python run_evaluation.py --model_path $LATEST_CHECKPOINT/best_model.pth --model_type vit

# Or run evaluation for ConvNeXt model
LATEST_CONVNEXT_CHECKPOINT=$(ls -t checkpoints/CONVNEXT_* | head -n 1)
uv run python run_evaluation.py --model_path $LATEST_CONVNEXT_CHECKPOINT/best_model.pth --model_type convnext

# Compute metrics
uv run python compute_metrics.py --predictions output/predictions.csv --weights weights --output output/eval_result.csv
```

### Evaluation Parameters

- `--model_path`: Path to model checkpoint file (required)
- `--model_type`: Model architecture type (vit or convnext, default: vit)

### Evaluation Results

Results are saved in `evaluation/output/`:
- `predictions.csv`: Individual predictions
- `eval_result.csv`: F1 score and model parameters
- `timing_results.json`: Performance metrics

### Class Mapping
- **0**: haze
- **1**: normal (cloud, land, seaside, dust)
- **2**: smoke/wildfire