#!/bin/bash
# Deploy services to Cloud Run

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
REPO_NAME="haze-prediction"

# Load CloudSQL config if exists
if [ -f /tmp/cloudsql-config.sh ]; then
  source /tmp/cloudsql-config.sh
fi

# Get connection name if not set
if [ -z "$CONNECTION_NAME" ]; then
  CONNECTION_NAME=$(gcloud sql instances describe haze-prediction-db \
    --project=${PROJECT_ID} \
    --format="value(connectionName)")
fi

echo "Deploying services to Cloud Run..."

# Deploy API service
echo "Deploying API service..."
gcloud run deploy haze-prediction-api \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-api:latest \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="FIRMS_MAP_KEY=firms-api-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=${CONNECTION_NAME} \
  --project=${PROJECT_ID}

# Deploy scheduler service
echo "Deploying Scheduler service..."
gcloud run deploy haze-prediction-scheduler \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-scheduler:latest \
  --region=${REGION} \
  --platform=managed \
  --no-allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=1 \
  --timeout=3600 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="FIRMS_MAP_KEY=firms-api-key:latest,DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=${CONNECTION_NAME} \
  --project=${PROJECT_ID}

# Get API URL
API_URL=$(gcloud run services describe haze-prediction-api \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(status.url)")

echo ""
echo "Deployment complete!"
echo "API URL: ${API_URL}"
echo ""
echo "Test endpoints:"
echo "  curl ${API_URL}/health"
echo "  curl ${API_URL}/predict/24h"
echo "  curl ${API_URL}/current/psi"
