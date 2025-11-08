#!/bin/bash
# Build and push Docker images to Artifact Registry

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
REPO_NAME="haze-prediction"

echo "Building and pushing Docker images..."

# Set image names
API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-api:latest"
SCHEDULER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/haze-scheduler:latest"

echo "Building API image..."
docker build -t ${API_IMAGE} .

echo "Building Scheduler image..."
docker build -t ${SCHEDULER_IMAGE} .

echo "Pushing API image..."
docker push ${API_IMAGE}

echo "Pushing Scheduler image..."
docker push ${SCHEDULER_IMAGE}

echo ""
echo "Docker images built and pushed successfully!"
echo "  API: ${API_IMAGE}"
echo "  Scheduler: ${SCHEDULER_IMAGE}"
