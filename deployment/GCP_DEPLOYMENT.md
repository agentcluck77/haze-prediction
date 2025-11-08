# GCP Deployment Guide - Singapore Haze Prediction System

This guide covers the complete deployment of the haze prediction system to Google Cloud Platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  Cloud Run   │         │  Cloud Run   │                  │
│  │  (API)       │────────▶│  (Scheduler) │                  │
│  │  Port: 8000  │         │              │                  │
│  └──────┬───────┘         └──────┬───────┘                  │
│         │                        │                           │
│         │                        │                           │
│         ▼                        ▼                           │
│  ┌─────────────────────────────────────┐                    │
│  │       Cloud SQL (PostgreSQL)        │                    │
│  │       Database: haze_prediction     │                    │
│  └─────────────────────────────────────┘                    │
│                                                               │
│  ┌─────────────────────────────────────┐                    │
│  │       Cloud Storage Buckets         │                    │
│  │   - ML Models                        │                    │
│  │   - Logs & Data                      │                    │
│  └─────────────────────────────────────┘                    │
│                                                               │
│  ┌─────────────────────────────────────┐                    │
│  │       Secret Manager                 │                    │
│  │   - FIRMS_MAP_KEY                    │                    │
│  │   - DATABASE_URL                     │                    │
│  │   - DB_PASSWORD                      │                    │
│  └─────────────────────────────────────┘                    │
│                                                               │
│  ┌─────────────────────────────────────┐                    │
│  │       Artifact Registry              │                    │
│  │   - haze-api:latest                  │                    │
│  │   - haze-scheduler:latest            │                    │
│  └─────────────────────────────────────┘                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. GCP Project created (Project ID: `hacx-477608`)
2. gcloud CLI installed and authenticated
3. Required GCP APIs enabled
4. Docker installed locally
5. Sufficient GCP permissions (Owner or Editor role)

## Cost Estimate

**Monthly estimates** (based on light production usage):
- Cloud Run (API): $10-30/month
- Cloud Run (Scheduler): $5-15/month
- Cloud SQL (db-f1-micro): $15-25/month
- Cloud Storage: $5-10/month
- Secret Manager: $1-2/month
- Artifact Registry: $0-5/month

**Total**: Approximately $35-90/month

## Deployment Steps

### Phase 1: Enable GCP Services

```bash
# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=hacx-477608
```

### Phase 2: Set Up Cloud SQL Database

```bash
# Create PostgreSQL instance
gcloud sql instances create haze-prediction-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-southeast1 \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=02:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=03 \
  --project=hacx-477608

# Create database
gcloud sql databases create haze_prediction \
  --instance=haze-prediction-db \
  --project=hacx-477608

# Create database user
gcloud sql users create hazeuser \
  --instance=haze-prediction-db \
  --password=YOUR_SECURE_PASSWORD \
  --project=hacx-477608

# Get connection name for later use
gcloud sql instances describe haze-prediction-db \
  --project=hacx-477608 \
  --format="value(connectionName)"
```

**Note**: Save the connection name, it will look like: `hacx-477608:asia-southeast1:haze-prediction-db`

### Phase 3: Set Up Storage

```bash
# Create bucket for ML models
gsutil mb -p hacx-477608 -c STANDARD -l asia-southeast1 gs://hacx-haze-models/

# Create bucket for data/logs
gsutil mb -p hacx-477608 -c STANDARD -l asia-southeast1 gs://hacx-haze-data/

# Upload ML models
gsutil -m cp -r models/* gs://hacx-haze-models/

# Set bucket permissions (if needed)
gsutil iam ch allUsers:objectViewer gs://hacx-haze-models/
```

### Phase 4: Configure Secret Manager

```bash
# Store FIRMS API key
echo -n "f6cd6de4fa5a42514a72c8525064e890" | \
  gcloud secrets create firms-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=hacx-477608

# Store database password
echo -n "YOUR_SECURE_PASSWORD" | \
  gcloud secrets create db-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=hacx-477608

# Construct and store DATABASE_URL
echo -n "postgresql://hazeuser:YOUR_SECURE_PASSWORD@/haze_prediction?host=/cloudsql/hacx-477608:asia-southeast1:haze-prediction-db" | \
  gcloud secrets create database-url \
  --data-file=- \
  --replication-policy=automatic \
  --project=hacx-477608
```

### Phase 5: Set Up Artifact Registry

```bash
# Create Docker repository
gcloud artifacts repositories create haze-prediction \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description="Docker images for haze prediction system" \
  --project=hacx-477608

# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
```

### Phase 6: Initialize Database Schema

```bash
# Create a temporary Cloud SQL Proxy connection
cloud-sql-proxy hacx-477608:asia-southeast1:haze-prediction-db &

# Run initialization script
PGPASSWORD=YOUR_SECURE_PASSWORD psql \
  -h 127.0.0.1 \
  -U hazeuser \
  -d haze_prediction \
  -f init-db.sql

# Kill the proxy
pkill cloud-sql-proxy
```

### Phase 7: Build and Push Docker Images

```bash
# Set variables
export PROJECT_ID=hacx-477608
export REGION=asia-southeast1
export REPO_NAME=haze-prediction

# Build API image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-api:latest .

# Build scheduler image (same Dockerfile, different CMD)
docker build \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-scheduler:latest \
  --build-arg CMD="python -m src.scheduler.tasks" \
  .

# Push images
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-api:latest
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-scheduler:latest
```

### Phase 8: Deploy API Service to Cloud Run

```bash
# Deploy API service
gcloud run deploy haze-prediction-api \
  --image=asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest \
  --region=asia-southeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="FIRMS_MAP_KEY=firms-api-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=hacx-477608:asia-southeast1:haze-prediction-db \
  --project=hacx-477608

# Get the service URL
gcloud run services describe haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608 \
  --format="value(status.url)"
```

### Phase 9: Deploy Scheduler Service to Cloud Run

```bash
# Deploy scheduler service
gcloud run deploy haze-prediction-scheduler \
  --image=asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-scheduler:latest \
  --region=asia-southeast1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="FIRMS_MAP_KEY=firms-api-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=hacx-477608:asia-southeast1:haze-prediction-db \
  --project=hacx-477608
```

### Phase 10: Verify Deployment

```bash
# Get API URL
export API_URL=$(gcloud run services describe haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608 \
  --format="value(status.url)")

# Test health endpoint
curl ${API_URL}/health

# Test prediction endpoint
curl ${API_URL}/predict/24h

# Test current PSI
curl ${API_URL}/current/psi

# Test current fires
curl ${API_URL}/current/fires
```

## Post-Deployment Configuration

### Set up Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=haze-prediction-api \
  --domain=api.haze-prediction.your-domain.com \
  --region=asia-southeast1 \
  --project=hacx-477608
```

### Set up Monitoring

```bash
# Create uptime check
gcloud monitoring uptime create haze-api-health \
  --resource-type=uptime-url \
  --host=${API_URL}/health \
  --display-name="Haze API Health Check" \
  --project=hacx-477608
```

### Configure Alerts

```bash
# Create alert policy for API errors
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Haze API Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --project=hacx-477608
```

## Updating the Deployment

### Update API Service

```bash
# Build and push new image
docker build -t asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest .
docker push asia-southeast1-docker.pkg.dev/hacx-477608/haze-prediction/haze-api:latest

# Deploy update
gcloud run services update haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608
```

### Update ML Models

```bash
# Upload new models
gsutil -m cp -r models/* gs://hacx-haze-models/

# Restart services to reload models
gcloud run services update haze-prediction-api --region=asia-southeast1 --project=hacx-477608
gcloud run services update haze-prediction-scheduler --region=asia-southeast1 --project=hacx-477608
```

## Troubleshooting

### View Logs

```bash
# API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=haze-prediction-api" \
  --limit=50 \
  --project=hacx-477608

# Scheduler logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=haze-prediction-scheduler" \
  --limit=50 \
  --project=hacx-477608

# Database logs
gcloud sql operations list --instance=haze-prediction-db --project=hacx-477608
```

### Connect to Database

```bash
# Start Cloud SQL Proxy
cloud-sql-proxy hacx-477608:asia-southeast1:haze-prediction-db

# Connect with psql
PGPASSWORD=YOUR_SECURE_PASSWORD psql -h 127.0.0.1 -U hazeuser -d haze_prediction
```

### Common Issues

1. **Connection to Cloud SQL fails**
   - Check that Cloud SQL Admin API is enabled
   - Verify the Cloud SQL instance is running
   - Ensure Cloud Run service has the Cloud SQL connection configured

2. **Models not found**
   - Verify models are uploaded to Cloud Storage
   - Check that the service has read permissions on the bucket
   - Ensure the models directory structure is correct

3. **External API calls fail**
   - Check that the service has internet access (default for Cloud Run)
   - Verify API keys are correct in Secret Manager
   - Check rate limits on external APIs

## Security Best Practices

1. **Database**
   - Use strong passwords
   - Enable SSL connections
   - Restrict network access
   - Regular backups enabled

2. **Secrets**
   - Never commit secrets to code
   - Use Secret Manager for all sensitive data
   - Rotate secrets regularly
   - Use IAM for access control

3. **Cloud Run**
   - Use --no-allow-unauthenticated for internal services
   - Configure CORS properly for API
   - Set up rate limiting
   - Enable HTTPS only

4. **Monitoring**
   - Set up logging alerts
   - Monitor error rates
   - Track API usage
   - Monitor costs

## Cost Optimization

1. **Cloud Run**
   - Use min-instances=0 for API (scale to zero)
   - Set appropriate CPU/memory limits
   - Use request-based scaling

2. **Cloud SQL**
   - Use appropriate tier (db-f1-micro for development)
   - Enable storage auto-increase
   - Schedule backups during low-traffic periods

3. **Cloud Storage**
   - Use Standard storage class
   - Set lifecycle policies for old data
   - Compress large files

## Rollback Procedure

```bash
# List revisions
gcloud run revisions list --service=haze-prediction-api --region=asia-southeast1

# Rollback to previous revision
gcloud run services update-traffic haze-prediction-api \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=asia-southeast1 \
  --project=hacx-477608
```

## Cleanup (Development/Testing)

```bash
# Delete Cloud Run services
gcloud run services delete haze-prediction-api --region=asia-southeast1 --project=hacx-477608
gcloud run services delete haze-prediction-scheduler --region=asia-southeast1 --project=hacx-477608

# Delete Cloud SQL instance
gcloud sql instances delete haze-prediction-db --project=hacx-477608

# Delete storage buckets
gsutil rm -r gs://hacx-haze-models/
gsutil rm -r gs://hacx-haze-data/

# Delete secrets
gcloud secrets delete firms-api-key --project=hacx-477608
gcloud secrets delete db-password --project=hacx-477608
gcloud secrets delete database-url --project=hacx-477608

# Delete artifact repository
gcloud artifacts repositories delete haze-prediction --location=asia-southeast1 --project=hacx-477608
```

## Next Steps

1. Set up CI/CD pipeline (Cloud Build)
2. Configure monitoring dashboards
3. Set up automated backups
4. Implement rate limiting
5. Add authentication for admin endpoints
6. Set up staging environment
7. Configure custom domain
8. Implement caching layer (Cloud Memorystore)
