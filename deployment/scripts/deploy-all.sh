#!/bin/bash
# Master deployment script - runs all deployment steps

set -e

echo "========================================="
echo "  Singapore Haze Prediction System"
echo "  GCP Deployment Script"
echo "========================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root
cd "${SCRIPT_DIR}/../.."

echo "Step 1: Enabling GCP services..."
bash ${SCRIPT_DIR}/01-enable-services.sh
echo ""

echo "Step 2: Setting up Cloud SQL..."
bash ${SCRIPT_DIR}/02-setup-cloudsql.sh
echo ""

echo "Step 3: Setting up Cloud Storage..."
bash ${SCRIPT_DIR}/03-setup-storage.sh
echo ""

echo "Step 4: Setting up Secret Manager..."
bash ${SCRIPT_DIR}/04-setup-secrets.sh
echo ""

echo "Step 5: Setting up Artifact Registry..."
bash ${SCRIPT_DIR}/05-setup-artifact-registry.sh
echo ""

echo "Step 6: Initializing database..."
bash ${SCRIPT_DIR}/06-init-database.sh
echo ""

echo "Step 7: Building and pushing Docker images..."
bash ${SCRIPT_DIR}/07-build-and-push.sh
echo ""

echo "Step 8: Deploying to Cloud Run..."
bash ${SCRIPT_DIR}/08-deploy-cloudrun.sh
echo ""

echo "Step 9: Testing deployment..."
bash ${SCRIPT_DIR}/09-test-deployment.sh
echo ""

echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
