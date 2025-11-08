# Quick Start - GCP Deployment

This guide will help you deploy the Singapore Haze Prediction System to Google Cloud Platform in under 30 minutes.

## Prerequisites

1. GCP account with billing enabled
2. Project created: `hacx-477608`
3. `gcloud` CLI installed and authenticated
4. Docker installed
5. `psql` client installed (for database initialization)
6. `cloud-sql-proxy` installed

### Install Prerequisites (macOS)

```bash
# Install gcloud CLI
brew install google-cloud-sdk

# Install Docker Desktop
brew install --cask docker

# Install PostgreSQL client
brew install postgresql

# Install Cloud SQL Proxy
brew install cloud-sql-proxy

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project hacx-477608
```

## Option 1: Automated Deployment (Recommended)

Run the master deployment script:

```bash
cd deployment/scripts
./deploy-all.sh
```

This script will:
1. Enable all required GCP services
2. Create Cloud SQL database
3. Set up Cloud Storage buckets
4. Configure Secret Manager
5. Set up Artifact Registry
6. Initialize database schema
7. Build and push Docker images
8. Deploy to Cloud Run
9. Run tests

You will be prompted for:
- Database password (choose a strong password)
- FIRMS API key (if not already set in environment)

The entire process takes approximately 15-20 minutes.

## Option 2: Manual Step-by-Step Deployment

If you prefer to run each step individually:

```bash
cd deployment/scripts

# Step 1: Enable GCP services
./01-enable-services.sh

# Step 2: Set up Cloud SQL (you'll be prompted for password)
./02-setup-cloudsql.sh

# Step 3: Set up Cloud Storage
./03-setup-storage.sh

# Step 4: Set up Secret Manager (you'll be prompted for API keys)
./04-setup-secrets.sh

# Step 5: Set up Artifact Registry
./05-setup-artifact-registry.sh

# Step 6: Initialize database schema
./06-init-database.sh

# Step 7: Build and push Docker images
./07-build-and-push.sh

# Step 8: Deploy to Cloud Run
./08-deploy-cloudrun.sh

# Step 9: Test deployment
./09-test-deployment.sh
```

## Environment Variables

Before running the deployment, you can optionally set these environment variables:

```bash
export FIRMS_MAP_KEY="your-firms-api-key"
export DB_PASSWORD="your-secure-database-password"
```

If not set, you'll be prompted during deployment.

## Post-Deployment

After deployment completes, you'll receive:
- API URL for your deployed service
- Test commands to verify functionality

Example output:
```
API URL: https://haze-prediction-api-xxxxx-xx.a.run.app

Test endpoints:
  curl https://haze-prediction-api-xxxxx-xx.a.run.app/health
  curl https://haze-prediction-api-xxxxx-xx.a.run.app/predict/24h
  curl https://haze-prediction-api-xxxxx-xx.a.run.app/current/psi
```

## Verify Deployment

Test all endpoints:

```bash
# Get API URL
export API_URL=$(gcloud run services describe haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608 \
  --format="value(status.url)")

# Test health
curl ${API_URL}/health

# Test prediction
curl ${API_URL}/predict/24h

# Test all predictions
curl ${API_URL}/predict/all

# Test current PSI
curl ${API_URL}/current/psi

# Test fire detections
curl ${API_URL}/current/fires
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Ensure you have proper permissions
   gcloud projects add-iam-policy-binding hacx-477608 \
     --member="user:YOUR_EMAIL" \
     --role="roles/editor"
   ```

2. **Docker Build Fails**
   ```bash
   # Ensure Docker is running
   docker ps

   # Re-authenticate Docker
   gcloud auth configure-docker asia-southeast1-docker.pkg.dev
   ```

3. **Cloud SQL Connection Fails**
   ```bash
   # Verify instance is running
   gcloud sql instances describe haze-prediction-db --project=hacx-477608

   # Check Cloud SQL Proxy
   ps aux | grep cloud-sql-proxy
   ```

4. **Models Not Found**
   ```bash
   # Verify models exist locally
   ls -la models/

   # Re-upload to Cloud Storage
   gsutil -m cp -r models/* gs://hacx-haze-models/
   ```

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
```

## Update Deployment

To update the application after making code changes:

```bash
cd deployment/scripts

# Rebuild and push images
./07-build-and-push.sh

# Redeploy services
./08-deploy-cloudrun.sh

# Test updated deployment
./09-test-deployment.sh
```

## Rollback

If something goes wrong, rollback to a previous version:

```bash
# List revisions
gcloud run revisions list \
  --service=haze-prediction-api \
  --region=asia-southeast1 \
  --project=hacx-477608

# Rollback to specific revision
gcloud run services update-traffic haze-prediction-api \
  --to-revisions=REVISION_NAME=100 \
  --region=asia-southeast1 \
  --project=hacx-477608
```

## Clean Up (Development/Testing)

To delete all resources:

```bash
# WARNING: This will delete all data and cannot be undone!

# Delete Cloud Run services
gcloud run services delete haze-prediction-api --region=asia-southeast1 --project=hacx-477608 --quiet
gcloud run services delete haze-prediction-scheduler --region=asia-southeast1 --project=hacx-477608 --quiet

# Delete Cloud SQL instance
gcloud sql instances delete haze-prediction-db --project=hacx-477608 --quiet

# Delete storage buckets
gsutil rm -r gs://hacx-haze-models/
gsutil rm -r gs://hacx-haze-data/

# Delete secrets
gcloud secrets delete firms-api-key --project=hacx-477608 --quiet
gcloud secrets delete db-password --project=hacx-477608 --quiet
gcloud secrets delete database-url --project=hacx-477608 --quiet

# Delete artifact repository
gcloud artifacts repositories delete haze-prediction \
  --location=asia-southeast1 \
  --project=hacx-477608 \
  --quiet
```

## Cost Management

Monitor your costs:

```bash
# View current billing
gcloud billing accounts list

# Set budget alerts in Cloud Console
# https://console.cloud.google.com/billing/budgets
```

Estimated monthly cost: $35-90 (see deployment/GCP_DEPLOYMENT.md for details)

## Next Steps

1. Set up monitoring and alerts
2. Configure custom domain
3. Enable Cloud CDN for better performance
4. Set up CI/CD pipeline
5. Configure staging environment

See `deployment/GCP_DEPLOYMENT.md` for detailed information on these topics.

## Support

For issues:
1. Check logs using commands above
2. Review `deployment/GCP_DEPLOYMENT.md` for detailed troubleshooting
3. Check GCP Console for service status

## Security Notes

- Never commit secrets to version control
- Use strong database passwords
- Regularly rotate API keys
- Monitor access logs
- Enable VPC Service Controls for production
