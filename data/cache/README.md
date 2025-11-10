# Feature Cache Directory

This directory stores pre-computed features to avoid re-running expensive feature engineering.

## Unified Cache Approach

We use a **single comprehensive cache** covering the full date range (2014-2024):
- Training loads the cache and filters to 2014-2023
- Evaluation loads the cache and filters to desired period (typically 2024)

This avoids computing features twice for overlapping periods.

## How It Works

**Generate cache once:**
```bash
python3 generate_eval_cache.py  # 10-30 minutes
```

**Then train (fast):**
```bash
python3 train_models.py  # 1-2 minutes (loads from cache)
```

**Total time saved: 10-30 minutes per experiment!**

## Cache Files

**Primary cache (used by both training and evaluation):**
- `eval_2014-04-01_2024-12-31_h6.csv` - Full dataset with 25 features

Format: `eval_{start_date}_{end_date}_h{sample_hours}.csv`

**Legacy training caches (deprecated):**
- `training_*` files are no longer used

## Usage

### Generate the cache:
```bash
python3 generate_eval_cache.py
```

This creates `eval_2014-04-01_2024-12-31_h6.csv` with 25 features.

### Training and evaluation automatically use this cache:
- `train_models.py` - Loads cache, filters to 2014-2023
- `src/evaluation/evaluate_models.py` - Loads cache, filters to desired period

## When to Rebuild

Rebuild the cache when you:
- Add new features (PSI lags, temporal features, etc.)
- Update feature engineering logic
- Add new data (2014-2015 fire/weather data)
- Modify feature calculations (fire risk, wind transport, etc.)

## Cache Invalidation

Delete the eval cache and regenerate:
```bash
rm data/cache/eval_*.csv
python3 generate_eval_cache.py
```

**Note:** This will take 10-30 minutes to regenerate, but only needs to be done when features change.
