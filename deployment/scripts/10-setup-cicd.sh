#!/bin/bash
# Set up CI/CD pipeline with Cloud Build

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
REPO_OWNER="your-github-username"  # Update this
REPO_NAME="hacx-extra"              # Update this

echo "Setting up CI/CD pipeline for Singapore Haze Prediction System"
echo ""

# Step 1: Enable Cloud Build API
echo "Step 1: Enabling Cloud Build API..."
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}

# Step 2: Grant Cloud Build permissions
echo "Step 2: Granting Cloud Build permissions..."

# Get Cloud Build service account
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant permissions to deploy to Cloud Run
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/run.admin"

# Grant permissions to access Secret Manager
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"

# Grant permissions to use service accounts
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

# Grant permissions to access Cloud Storage
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/storage.admin"

# Grant permissions to access Cloud SQL
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/cloudsql.client"

echo ""
echo "Permissions granted successfully!"
echo ""

# Step 3: Connect GitHub repository
echo "Step 3: Connecting GitHub repository..."
echo ""
echo "MANUAL STEP REQUIRED:"
echo "1. Go to: https://console.cloud.google.com/cloud-build/triggers/connect?project=${PROJECT_ID}"
echo "2. Select 'GitHub (Cloud Build GitHub App)'"
echo "3. Authenticate with GitHub"
echo "4. Select your repository: ${REPO_OWNER}/${REPO_NAME}"
echo "5. Click 'Connect'"
echo ""
echo "Press Enter after you've completed the GitHub connection..."
read

# Step 4: Create Cloud Build trigger
echo "Step 4: Creating Cloud Build trigger..."

# Check if trigger already exists
TRIGGER_NAME="deploy-on-push-main"
if gcloud builds triggers describe ${TRIGGER_NAME} --project=${PROJECT_ID} 2>/dev/null; then
  echo "Trigger ${TRIGGER_NAME} already exists. Updating..."
  gcloud builds triggers delete ${TRIGGER_NAME} --project=${PROJECT_ID} --quiet
fi

# Create new trigger
gcloud builds triggers create github \
  --name=${TRIGGER_NAME} \
  --repo-name=${REPO_NAME} \
  --repo-owner=${REPO_OWNER} \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --project=${PROJECT_ID} \
  --region=${REGION}

echo ""
echo "========================================="
echo "  CI/CD Pipeline Setup Complete!"
echo "========================================="
echo ""
echo "Trigger Name: ${TRIGGER_NAME}"
echo "Trigger Event: Push to main branch"
echo "Build Config: cloudbuild.yaml"
echo ""
echo "Next steps:"
echo "1. Commit cloudbuild.yaml to your repository"
echo "2. Push to main branch to trigger first build"
echo "3. Monitor builds at: https://console.cloud.google.com/cloud-build/builds?project=${PROJECT_ID}"
echo ""
echo "Test the trigger:"
echo "  git add cloudbuild.yaml"
echo "  git commit -m 'Add CI/CD pipeline'"
echo "  git push origin main"
echo ""
