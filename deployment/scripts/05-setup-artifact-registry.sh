#!/bin/bash
# Set up Artifact Registry for Docker images

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
REPO_NAME="haze-prediction"

echo "Setting up Artifact Registry..."

# Create repository
if gcloud artifacts repositories describe ${REPO_NAME} \
  --location=${REGION} \
  --project=${PROJECT_ID} 2>/dev/null; then
  echo "Repository ${REPO_NAME} already exists"
else
  echo "Creating Docker repository: ${REPO_NAME}"
  gcloud artifacts repositories create ${REPO_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Docker images for haze prediction system" \
    --project=${PROJECT_ID}
fi

# Configure Docker authentication
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo ""
echo "Artifact Registry setup complete!"
echo "Repository: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
