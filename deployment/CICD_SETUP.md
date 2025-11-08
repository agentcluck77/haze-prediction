# CI/CD Pipeline Setup Guide

This guide explains how to set up continuous integration and deployment for the Singapore Haze Prediction System using Google Cloud Build.

## Overview

The CI/CD pipeline automatically:
1. Builds Docker images when code is pushed to main branch
2. Pushes images to Artifact Registry with version tags
3. Deploys the updated API to Cloud Run
4. Uploads ML models to Cloud Storage
5. Runs tests (optional)

## Architecture

```
GitHub (main branch)
        ↓
    Push Event
        ↓
  Cloud Build Trigger
        ↓
   cloudbuild.yaml
        ↓
    ┌──────────────────┐
    │ Build & Test     │
    │ - Build images   │
    │ - Run tests      │
    │ - Push to Artifact│
    └──────────────────┘
        ↓
    ┌──────────────────┐
    │ Deploy           │
    │ - Update Cloud Run│
    │ - Upload models  │
    └──────────────────┘
        ↓
   Production API
```

## Prerequisites

1. GitHub repository for your code
2. GCP project with billing enabled
3. Existing Cloud Run service deployed
4. Cloud Build API enabled

## Setup Instructions

### Option 1: Automated Setup (Recommended)

Run the setup script:

```bash
cd deployment/scripts
./10-setup-cicd.sh
```

This will:
1. Enable Cloud Build API
2. Grant necessary permissions
3. Guide you through GitHub connection
4. Create the build trigger

### Option 2: Manual Setup

#### Step 1: Enable Cloud Build API

```bash
gcloud services enable cloudbuild.googleapis.com --project=hacx-477608
```

#### Step 2: Grant Permissions to Cloud Build

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe hacx-477608 --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run admin
gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/run.admin"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"

# Grant service account user
gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

# Grant Cloud Storage admin
gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/storage.admin"

# Grant Cloud SQL client
gcloud projects add-iam-policy-binding hacx-477608 \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/cloudsql.client"
```

#### Step 3: Connect GitHub Repository

1. Go to Cloud Build Triggers page:
   ```
   https://console.cloud.google.com/cloud-build/triggers/connect?project=hacx-477608
   ```

2. Select **"GitHub (Cloud Build GitHub App)"**

3. Click **"Authenticate"** and sign in to GitHub

4. Select your repository and click **"Connect"**

#### Step 4: Create Build Trigger

Using gcloud CLI:

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

Or use the Cloud Console:
1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers?project=hacx-477608)
2. Click **"CREATE TRIGGER"**
3. Configure:
   - Name: `deploy-on-push-main`
   - Event: Push to a branch
   - Source: Your GitHub repository
   - Branch: `^main$`
   - Configuration: Cloud Build configuration file
   - Location: `/cloudbuild.yaml`
4. Click **"CREATE"**

#### Step 5: Commit and Push

```bash
git add cloudbuild.yaml
git commit -m "Add CI/CD pipeline configuration"
git push origin main
```

## Build Configuration (cloudbuild.yaml)

The pipeline consists of these steps:

### 1. Build Docker Images
```yaml
- Build API image with linux/amd64 platform
- Build Scheduler image with linux/amd64 platform
- Tag with both commit SHA and 'latest'
```

### 2. Push to Artifact Registry
```yaml
- Push API image with all tags
- Push Scheduler image with all tags
```

### 3. Deploy to Cloud Run
```yaml
- Deploy API service with new image
- Configure environment variables
- Set secrets from Secret Manager
- Connect to Cloud SQL
```

### 4. Upload Models
```yaml
- Sync models directory to Cloud Storage
- Only if models directory exists
```

### 5. Run Tests (Optional)
```yaml
- Install dependencies
- Run pytest
- Currently commented out
```

## Build Variables

The build uses these substitution variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `${PROJECT_ID}` | GCP Project ID | hacx-477608 |
| `${SHORT_SHA}` | Git commit SHA (short) | Auto |
| `${REGION}` | GCP region | asia-southeast1 |
| `${SERVICE_NAME}` | Cloud Run service name | haze-prediction-api |

## Monitoring Builds

### View Build History

Cloud Console:
```
https://console.cloud.google.com/cloud-build/builds?project=hacx-477608
```

Command line:
```bash
gcloud builds list --project=hacx-477608 --limit=10
```

### View Build Logs

For a specific build:
```bash
BUILD_ID="your-build-id"
gcloud builds log ${BUILD_ID} --project=hacx-477608
```

Real-time streaming:
```bash
gcloud builds log ${BUILD_ID} --stream --project=hacx-477608
```

### Build Notifications

Set up notifications for build status:

```bash
# Create a Pub/Sub topic
gcloud pubsub topics create cloud-builds --project=hacx-477608

# Create email subscription (optional)
gcloud pubsub subscriptions create build-notifications \
  --topic=cloud-builds \
  --project=hacx-477608
```

## Trigger Management

### List Triggers

```bash
gcloud builds triggers list --project=hacx-477608
```

### Update Trigger

```bash
gcloud builds triggers update deploy-on-push-main \
  --branch-pattern="^main$|^develop$" \
  --project=hacx-477608
```

### Delete Trigger

```bash
gcloud builds triggers delete deploy-on-push-main \
  --project=hacx-477608
```

### Manually Run Trigger

```bash
gcloud builds triggers run deploy-on-push-main \
  --branch=main \
  --project=hacx-477608
```

## Testing the Pipeline

### 1. Make a Simple Change

```bash
# Update README or add a comment
echo "# Test CI/CD" >> README.md
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main
```

### 2. Monitor the Build

```bash
# List recent builds
gcloud builds list --limit=1 --project=hacx-477608

# Get build ID and stream logs
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)" --project=hacx-477608)
gcloud builds log ${BUILD_ID} --stream --project=hacx-477608
```

### 3. Verify Deployment

```bash
# Check Cloud Run revision
gcloud run revisions list \
  --service=haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608

# Test API
curl https://haze-prediction-api-1092946108581.asia-southeast1.run.app/health
```

## Build Time & Cost

**Typical build times:**
- Image build: 3-5 minutes
- Tests: 1-2 minutes (if enabled)
- Deployment: 1-2 minutes
- **Total: 5-10 minutes**

**Cost estimates:**
- Free tier: 120 build-minutes/day
- After free tier: $0.003/build-minute
- Typical build: ~$0.03-0.05
- Monthly (30 builds): ~$1-2

## Troubleshooting

### Build Fails: Permission Denied

Check Cloud Build service account permissions:
```bash
PROJECT_NUMBER=$(gcloud projects describe hacx-477608 --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Verify permissions
gcloud projects get-iam-policy hacx-477608 \
  --flatten="bindings[].members" \
  --filter="bindings.members:${BUILD_SA}"
```

### Build Fails: Image Platform Error

Ensure `--platform=linux/amd64` is specified in docker build commands.

### Deployment Fails: Service Not Found

Create the service first using manual deployment, then CI/CD can update it.

### Trigger Not Firing

1. Check trigger configuration:
   ```bash
   gcloud builds triggers describe deploy-on-push-main --project=hacx-477608
   ```

2. Verify GitHub app is installed:
   ```
   https://github.com/settings/installations
   ```

3. Check branch name matches pattern (exactly `main`)

### Build Timeout

Increase timeout in cloudbuild.yaml:
```yaml
timeout: 1800s  # 30 minutes
```

## Advanced Configuration

### Environment-Specific Deployments

Create separate triggers for different environments:

**Staging (develop branch):**
```bash
gcloud builds triggers create github \
  --name=deploy-staging \
  --repo-name=hacx-extra \
  --repo-owner=YOUR_USERNAME \
  --branch-pattern="^develop$" \
  --build-config=cloudbuild-staging.yaml \
  --project=hacx-477608
```

**Production (main branch):**
```bash
gcloud builds triggers create github \
  --name=deploy-production \
  --repo-name=hacx-extra \
  --repo-owner=YOUR_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --project=hacx-477608
```

### Add Tests to Pipeline

Uncomment the test step in cloudbuild.yaml:
```yaml
- name: 'python:3.13-slim'
  id: 'run-tests'
  entrypoint: bash
  args:
    - '-c'
    - |
      pip install -r requirements.txt
      pytest tests/ -v --cov=src
```

### Rollback on Test Failure

Add conditional deployment:
```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-api'
  entrypoint: bash
  args:
    - '-c'
    - |
      if [ "$?" -eq 0 ]; then
        gcloud run deploy haze-prediction-api ...
      else
        echo "Tests failed, skipping deployment"
        exit 1
      fi
  waitFor: ['run-tests']
```

### Slack Notifications

Add Slack notification step:
```yaml
- name: 'gcr.io/cloud-builders/curl'
  args:
    - '-X'
    - 'POST'
    - '-H'
    - 'Content-Type: application/json'
    - '-d'
    - '{"text":"Build $BUILD_ID completed for commit $SHORT_SHA"}'
    - '${_SLACK_WEBHOOK_URL}'
  secretEnv: ['SLACK_WEBHOOK_URL']
```

## Security Best Practices

1. **Least Privilege**: Grant only necessary permissions to Cloud Build SA
2. **Secret Management**: Use Secret Manager for sensitive data
3. **Image Scanning**: Enable vulnerability scanning in Artifact Registry
4. **Branch Protection**: Enable branch protection rules on main
5. **Review Process**: Require PR reviews before merging to main

## Next Steps

1. [ ] Set up staging environment with separate trigger
2. [ ] Enable automated tests in pipeline
3. [ ] Add vulnerability scanning
4. [ ] Configure build notifications (Slack/Email)
5. [ ] Implement blue/green deployments
6. [ ] Add performance testing step
7. [ ] Set up automated rollback on errors

## Resources

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Cloud Build Triggers](https://cloud.google.com/build/docs/automating-builds/create-manage-triggers)
- [Cloud Run Deployments](https://cloud.google.com/run/docs/deploying)
- [Build Configuration Reference](https://cloud.google.com/build/docs/build-config-file-schema)
