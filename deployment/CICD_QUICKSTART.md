# CI/CD Quick Start Guide

This guide will help you set up automated deployments for every push to the main branch.

## Prerequisites Completed

✓ Cloud Build API enabled
✓ Cloud Build service account permissions granted
✓ `cloudbuild.yaml` configuration file created

## Next Steps

### Step 1: Connect Your GitHub Repository

You need to connect your GitHub repository to Cloud Build:

1. **Open Cloud Build Triggers page**:
   ```
   https://console.cloud.google.com/cloud-build/triggers/connect?project=hacx-477608
   ```

2. **Select Source**:
   - Click on "GitHub (Cloud Build GitHub App)"

3. **Authenticate with GitHub**:
   - Click "Authenticate"
   - Sign in to your GitHub account
   - Authorize Google Cloud Build

4. **Select Repository**:
   - Choose your repository (e.g., `your-username/hacx-extra`)
   - Click "Connect"

5. **Done!**
   - You should see your repository listed as connected

### Step 2: Create the Build Trigger

After connecting GitHub, create a trigger that runs on every push to main:

**Option A: Using gcloud CLI (Recommended)**

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:

```bash
gcloud builds triggers create github \
  --name=deploy-on-push-main \
  --repo-name=hacx-extra \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --project=hacx-477608 \
  --region=asia-southeast1
```

**Option B: Using Cloud Console**

1. Go to https://console.cloud.google.com/cloud-build/triggers?project=hacx-477608
2. Click "CREATE TRIGGER"
3. Configure:
   - **Name**: `deploy-on-push-main`
   - **Event**: Push to a branch
   - **Source**: Select your connected repository
   - **Branch**: `^main$` (regex pattern)
   - **Configuration**: Cloud Build configuration file (cloudbuild.yaml)
   - **Location**: `/cloudbuild.yaml`
4. Click "CREATE"

### Step 3: Push to GitHub

Now commit and push the cloudbuild.yaml file to your repository:

```bash
# Add the CI/CD configuration
git add cloudbuild.yaml

# Commit
git commit -m "Add CI/CD pipeline with Cloud Build"

# Push to main branch (this will trigger the build!)
git push origin main
```

### Step 4: Monitor the Build

Watch your first automated build:

**Cloud Console**:
```
https://console.cloud.google.com/cloud-build/builds?project=hacx-477608
```

**Command Line**:
```bash
# List recent builds
gcloud builds list --limit=5 --project=hacx-477608

# Stream logs for the latest build
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)" --project=hacx-477608)
gcloud builds log ${BUILD_ID} --stream --project=hacx-477608
```

### Step 5: Verify Deployment

Once the build completes (5-10 minutes), verify the deployment:

```bash
# Check the latest Cloud Run revision
gcloud run revisions list \
  --service=haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608 \
  --limit=1

# Test the API
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/health
```

## What Happens on Each Push?

Every time you push to the `main` branch, Cloud Build automatically:

1. **Builds** Docker images for your API (tagged with git commit SHA + 'latest')
2. **Pushes** images to Artifact Registry
3. **Deploys** updated API to Cloud Run
4. **Uploads** ML models to Cloud Storage
5. **Notifies** you of build status

Total time: ~5-10 minutes per deployment

## Testing Your Pipeline

Make a test change and push:

```bash
# Make a small change
echo "# CI/CD Test" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main

# Watch the build
gcloud builds list --limit=1 --project=hacx-477608
```

## Build Status

You can check if your build succeeded:

```bash
# Get latest build status
gcloud builds list --limit=1 --format="table(id,status,createTime)" --project=hacx-477608
```

Status values:
- `WORKING`: Build in progress
- `SUCCESS`: Build completed successfully
- `FAILURE`: Build failed (check logs)
- `TIMEOUT`: Build exceeded time limit

## Common Issues

### Issue: Trigger doesn't fire

**Solution**:
- Verify GitHub app is installed: https://github.com/settings/installations
- Check trigger branch pattern matches exactly `main`
- Ensure cloudbuild.yaml is in repository root

### Issue: Build fails with permission error

**Solution**:
```bash
# Re-run permission grants
PROJECT_NUMBER=$(gcloud projects describe hacx-477608 --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/run.admin"
```

### Issue: Deployment fails

**Solution**: Check the logs:
```bash
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)" --project=hacx-477608)
gcloud builds log ${BUILD_ID} --project=hacx-477608
```

## Cost

**Free Tier**: 120 build-minutes per day (FREE)

**After free tier**:
- $0.003 per build-minute
- Typical build: ~8 minutes = $0.024
- 30 builds/month ≈ $0.72/month

## Next Steps

Once your CI/CD is working:

1. **Add tests** to the pipeline (uncomment test step in cloudbuild.yaml)
2. **Set up staging environment** for testing before production
3. **Configure notifications** (Slack, email) for build status
4. **Add branch protection** rules on GitHub to require reviews

## Support

- **Cloud Build Docs**: https://cloud.google.com/build/docs
- **Build History**: https://console.cloud.google.com/cloud-build/builds?project=hacx-477608
- **Triggers**: https://console.cloud.google.com/cloud-build/triggers?project=hacx-477608

## Summary

Your CI/CD pipeline is 90% ready! Just:
1. Connect GitHub repository (5 minutes)
2. Create build trigger (2 minutes)
3. Push cloudbuild.yaml to main

Then every push to main = automatic deployment! 🚀
