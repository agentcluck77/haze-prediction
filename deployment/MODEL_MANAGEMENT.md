# Model Management Strategy

## Overview

The ML models are managed **directly within the Docker images** rather than separately in Cloud Storage. This ensures models are always in sync with the code.

## How It Works

### Build Process

```
models/               # Local directory with .pkl files
   ↓
Dockerfile           # COPY models/ ./models/
   ↓
Docker Image         # Models bundled inside
   ↓
Cloud Run            # Deploys with latest models
```

### Benefits

1. **Always in Sync**: Models deployed match the code version exactly
2. **No External Dependencies**: No need to fetch from GCS at runtime
3. **Faster Startup**: Models load from local filesystem
4. **Version Control**: Models are versioned with code in Git
5. **Simpler CI/CD**: One build includes everything

## Updating Models

### Method 1: Local Development

```bash
# 1. Retrain models locally
python train_models.py

# 2. Verify new models
ls -lh models/

# 3. Commit and push
git add models/
git commit -m "Update ML models - improved accuracy"
git push origin main

# 4. CI/CD automatically builds and deploys new image with updated models
```

### Method 2: Direct Replacement

```bash
# Replace specific model
cp new_model.pkl models/linear_regression_24h.pkl

# Commit and push
git add models/linear_regression_24h.pkl
git commit -m "Update 24h prediction model"
git push origin main
```

## Model Files

Current models in the repository:

```
models/
├── linear_regression_24h.pkl   # 24-hour PSI prediction
├── linear_regression_48h.pkl   # 48-hour PSI prediction
├── linear_regression_72h.pkl   # 72-hour PSI prediction
└── linear_regression_7d.pkl    # 7-day PSI prediction
```

## Model Loading in Code

Models are loaded from the local filesystem:

```python
# src/api/prediction.py
def predict_psi(horizon: str = '24h', models_dir: str = 'models') -> dict:
    # Loads from /app/models/ inside the container
    model = load_model(models_dir, f'linear_regression_{horizon}.pkl')
```

## Git LFS (Optional)

If your models become very large (>100MB), consider using Git LFS:

```bash
# Install Git LFS
brew install git-lfs
git lfs install

# Track .pkl files
git lfs track "*.pkl"
git add .gitattributes

# Commit as usual
git add models/
git commit -m "Add models with Git LFS"
git push origin main
```

Current model sizes are small (~3KB each), so Git LFS is not necessary yet.

## Cloud Storage Backup (Optional)

While models are in Docker images, you can optionally keep a backup in GCS:

```bash
# Manual backup
gsutil -m cp models/* gs://hacx-haze-models/backup/$(date +%Y%m%d)/

# Or automate in cloudbuild.yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: bash
  args:
    - '-c'
    - 'gsutil -m cp models/* gs://hacx-haze-models/backup/$(date +%Y%m%d)/'
```

## Rollback Strategy

If new models cause issues, rollback is simple:

### Option 1: Git Revert
```bash
# Revert the commit with bad models
git revert <commit-hash>
git push origin main

# CI/CD redeploys with previous models
```

### Option 2: Cloud Run Revision
```bash
# List revisions
gcloud run revisions list \
  --service=haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608

# Rollback to previous revision
gcloud run services update-traffic haze-prediction-api \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=asia-southeast1 \
  --project=hacx-477608
```

## Model Training Workflow

Recommended workflow for model updates:

```bash
# 1. Create feature branch
git checkout -b update-models

# 2. Retrain models
python train_models.py

# 3. Test locally
pytest tests/test_model_training.py

# 4. Test API with new models
uvicorn src.api.main:app --reload
curl http://localhost:8000/predict/24h

# 5. Commit and push
git add models/
git commit -m "Update models: improved MAE from 15.0 to 12.5"
git push origin update-models

# 6. Create PR and merge to main
# 7. CI/CD automatically deploys
```

## Monitoring Model Performance

Track model performance in production:

```bash
# Check predictions
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/predict/24h

# View metrics
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/metrics/24h
```

## Best Practices

1. **Version Models**: Include training date or version in commit message
2. **Test Before Deploy**: Run tests with new models locally first
3. **Document Changes**: Note what changed (features, data, hyperparameters)
4. **Monitor Metrics**: Track MAE/RMSE after deployment
5. **Gradual Rollout**: Consider canary deployments for major model changes

## Example Commit Messages

Good commit messages for model updates:

```
✓ Update models: Retrained with 3 months additional data
✓ Improve 24h model: MAE reduced from 15.0 to 12.8
✓ Fix 72h model: Corrected feature normalization issue
✓ Models v2.0: Switch to Random Forest algorithm
```

## FAQ

**Q: Why not use Cloud Storage for models?**
A: Bundling models in Docker ensures version consistency and eliminates runtime dependencies. The small model size (~3KB) makes this practical.

**Q: What if models get too large?**
A: Use Git LFS for files >100MB, or switch to GCS if models exceed Docker image size limits (10GB).

**Q: How do I version models independently from code?**
A: Tag releases in Git (e.g., `v1.0.0-models-20250108`) or use semantic versioning in model filenames.

**Q: Can I deploy models without redeploying code?**
A: Not with this approach. If you need that flexibility, consider using GCS with model versioning.

**Q: How do I A/B test models?**
A: Deploy two Cloud Run services with different model versions and split traffic between them.

## Migration from GCS (If Previously Used)

If you were using Cloud Storage:

1. Remove GCS model loading code
2. Update `models_dir='models'` (already default)
3. Delete GCS bucket or keep as backup
4. Update CI/CD to remove GCS upload step (already done)

## Summary

✓ Models are in Git repository (`models/`)
✓ Dockerfile copies them into image
✓ CI/CD builds new image on every push
✓ Models always match code version
✓ Simple rollback via Git or Cloud Run revisions
