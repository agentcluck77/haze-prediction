#!/bin/bash
# Set up Cloud SQL PostgreSQL instance

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"
INSTANCE_NAME="haze-prediction-db"
DATABASE_NAME="haze_prediction"
DB_USER="hazeuser"

echo "Setting up Cloud SQL instance: ${INSTANCE_NAME}"

# Check if instance already exists
if gcloud sql instances describe ${INSTANCE_NAME} --project=${PROJECT_ID} 2>/dev/null; then
  echo "Instance ${INSTANCE_NAME} already exists. Skipping creation."
else
  echo "Creating PostgreSQL instance..."
  gcloud sql instances create ${INSTANCE_NAME} \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=${REGION} \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=02:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=03 \
    --project=${PROJECT_ID}

  echo "Waiting for instance to be ready..."
  sleep 30
fi

# Create database
echo "Creating database: ${DATABASE_NAME}"
gcloud sql databases create ${DATABASE_NAME} \
  --instance=${INSTANCE_NAME} \
  --project=${PROJECT_ID} 2>/dev/null || echo "Database already exists"

# Prompt for password
echo ""
echo "Enter a secure password for database user '${DB_USER}':"
read -s DB_PASSWORD

# Create user
echo "Creating database user..."
gcloud sql users create ${DB_USER} \
  --instance=${INSTANCE_NAME} \
  --password=${DB_PASSWORD} \
  --project=${PROJECT_ID} 2>/dev/null || echo "User already exists"

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe ${INSTANCE_NAME} \
  --project=${PROJECT_ID} \
  --format="value(connectionName)")

echo ""
echo "Cloud SQL setup complete!"
echo "Connection name: ${CONNECTION_NAME}"
echo ""
echo "IMPORTANT: Save this information:"
echo "  DB_PASSWORD=${DB_PASSWORD}"
echo "  CONNECTION_NAME=${CONNECTION_NAME}"
echo ""

# Save to temporary file for next scripts
cat > /tmp/cloudsql-config.sh << EOF
export DB_PASSWORD="${DB_PASSWORD}"
export CONNECTION_NAME="${CONNECTION_NAME}"
EOF

echo "Configuration saved to /tmp/cloudsql-config.sh"
