# HacX ViT-B/16 Training

Training ViT-B/16 model at 384 resolution with full fine-tuning on HacX dataset.

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

Start training with default settings:
```bash
uv run python train_vit.py
```

### Custom Training Parameters

```bash
uv run python train_vit.py \
  --batch_size 8 \
  --num_epochs 50 \
  --learning_rate 3e-5 \
  --data_dir HacX-dataset \
  --save_dir checkpoints
```

### Parameters

- `--batch_size`: Batch size (default: 8, optimized for GTX 4090)
- `--num_epochs`: Number of training epochs (default: 50)
- `--learning_rate`: Learning rate (default: 3e-5)
- `--data_dir`: Path to dataset (default: HacX-dataset)
- `--save_dir`: Checkpoint directory (default: checkpoints)
- `--project_name`: WandB project name
- `--run_name`: WandB run name

## Model Details

- **Architecture**: ViT-B/16 (384x384 input)
- **Training**: Full fine-tuning (all parameters updated)
- **Classes**: 3 (haze, normal, smoke)
- **Optimization**: AdamW with cosine scheduler
- **Mixed Precision**: Enabled for GTX 4090 optimization

## Monitoring

Training progress is logged to Weights & Biases. Set your `WANDB_API_KEY` environment variable to enable logging.

## Checkpoints

- Best model saved as `checkpoints/best_model.pth`
- Regular checkpoints saved every 5 epochs

## Model Evaluation

After training, evaluate your model using the evaluation system:

### Quick Evaluation

```bash
# Copy trained model to evaluation directory
cp checkpoints/best_model.pth evaluation/weights/vit_b16_hacx.pth

# Run evaluation
cd evaluation
uv run python run_evaluation.py

# Compute metrics
uv run python compute_metrics.py --predictions output/predictions.csv --weights weights --output output/eval_result.csv
```

### Evaluation Results

Results are saved in `evaluation/output/`:
- `predictions.csv`: Individual predictions
- `eval_result.csv`: F1 score and model parameters
- `timing_results.json`: Performance metrics

### Class Mapping
- **0**: haze
- **1**: normal (cloud, land, seaside, dust)
- **2**: smoke/wildfire