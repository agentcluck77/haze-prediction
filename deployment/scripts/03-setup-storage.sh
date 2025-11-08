#!/bin/bash
# Set up Cloud Storage buckets

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
MODELS_BUCKET="hacx-haze-models"
DATA_BUCKET="hacx-haze-data"

echo "Setting up Cloud Storage buckets..."

# Create models bucket
if gsutil ls -p ${PROJECT_ID} gs://${MODELS_BUCKET}/ 2>/dev/null; then
  echo "Bucket ${MODELS_BUCKET} already exists"
else
  echo "Creating models bucket: ${MODELS_BUCKET}"
  gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${MODELS_BUCKET}/
fi

# Create data bucket
if gsutil ls -p ${PROJECT_ID} gs://${DATA_BUCKET}/ 2>/dev/null; then
  echo "Bucket ${DATA_BUCKET} already exists"
else
  echo "Creating data bucket: ${DATA_BUCKET}"
  gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${DATA_BUCKET}/
fi

# Upload ML models if they exist
if [ -d "models" ]; then
  echo "Uploading ML models..."
  gsutil -m cp -r models/* gs://${MODELS_BUCKET}/
  echo "Models uploaded successfully"
else
  echo "Warning: models directory not found. Skipping model upload."
fi

echo "Cloud Storage setup complete!"
