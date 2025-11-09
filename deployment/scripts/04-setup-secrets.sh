#!/bin/bash
# Set up Secret Manager secrets

set -e

PROJECT_ID="hacx-477608"

echo "Setting up Secret Manager..."

# Load CloudSQL config if exists
if [ -f /tmp/cloudsql-config.sh ]; then
  source /tmp/cloudsql-config.sh
fi

# Prompt for FIRMS API key if not set
if [ -z "$FIRMS_MAP_KEY" ]; then
  echo "Enter FIRMS API key:"
  read FIRMS_MAP_KEY
fi

# Prompt for DB password if not set
if [ -z "$DB_PASSWORD" ]; then
  echo "Enter database password:"
  read -s DB_PASSWORD
fi

# Prompt for connection name if not set
if [ -z "$CONNECTION_NAME" ]; then
  echo "Enter Cloud SQL connection name (e.g., hacx-477608:asia-southeast1:haze-prediction-db):"
  read CONNECTION_NAME
fi

# Create FIRMS API key secret
echo "Creating FIRMS API key secret..."
echo -n "${FIRMS_MAP_KEY}" | \
  gcloud secrets create firms-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=${PROJECT_ID} 2>/dev/null || \
  echo -n "${FIRMS_MAP_KEY}" | \
  gcloud secrets versions add firms-api-key --data-file=- --project=${PROJECT_ID}

# Create database password secret
echo "Creating database password secret..."
echo -n "${DB_PASSWORD}" | \
  gcloud secrets create db-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=${PROJECT_ID} 2>/dev/null || \
  echo -n "${DB_PASSWORD}" | \
  gcloud secrets versions add db-password --data-file=- --project=${PROJECT_ID}

# Create DATABASE_URL secret
DATABASE_URL="postgresql://hazeuser:${DB_PASSWORD}@/haze_prediction?host=/cloudsql/${CONNECTION_NAME}"
echo "Creating DATABASE_URL secret..."
echo -n "${DATABASE_URL}" | \
  gcloud secrets create database-url \
  --data-file=- \
  --replication-policy=automatic \
  --project=${PROJECT_ID} 2>/dev/null || \
  echo -n "${DATABASE_URL}" | \
  gcloud secrets versions add database-url --data-file=- --project=${PROJECT_ID}

echo ""
echo "Secret Manager setup complete!"
echo "Created secrets:"
echo "  - firms-api-key"
echo "  - db-password"
echo "  - database-url"
