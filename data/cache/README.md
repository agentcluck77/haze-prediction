# Feature Cache Directory

This directory stores pre-computed training features to avoid re-running expensive feature engineering.

## How It Works

**First training run:**
```
1. Feature engineering: ~5-10 minutes
   - Load fire data
   - Load weather data
   - Process timestamps (DBSCAN, trajectories, etc.)
   - Save to cache

2. Model training: ~5 seconds
```

**Subsequent training runs:**
```
1. Load cached features: ~5 seconds
2. Model training: ~5 seconds
```

**Total time saved: 5-10 minutes per experiment!**

## Cache Files

Format: `training_{start_date}_{end_date}_h{sample_hours}.csv`

Examples:
- `training_2016-02-01_2023-12-31_h6.csv` - Training set (6-hour sampling)
- `training_2024-01-01_2024-12-31_h6.csv` - Test set (6-hour sampling)

## Usage

### Use cache (default):
```python
from src.training.data_preparation import prepare_training_dataset

df = prepare_training_dataset(
    start_date='2016-02-01',
    end_date='2023-12-31',
    sample_hours=6,
    use_cache=True  # Loads from cache if available
)
```

### Force rebuild (ignore cache):
```python
df = prepare_training_dataset(
    start_date='2016-02-01',
    end_date='2023-12-31',
    sample_hours=6,
    force_rebuild=True  # Recompute features
)
```

### Disable caching entirely:
```python
df = prepare_training_dataset(
    start_date='2016-02-01',
    end_date='2023-12-31',
    sample_hours=6,
    use_cache=False  # Don't save or load cache
)
```

## When to Rebuild

Rebuild the cache when you:
- Update feature engineering logic
- Change data sources (new fire/weather data)
- Modify feature calculations

## Cache Invalidation

Simply delete the cache file:
```bash
rm data/cache/training_*.csv
```

Or use `force_rebuild=True` in code.
