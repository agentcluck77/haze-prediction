#!/bin/bash
# Initialize database schema

set -e

PROJECT_ID="hacx-477608"
INSTANCE_NAME="haze-prediction-db"
DB_NAME="haze_prediction"
DB_USER="hazeuser"

echo "Initializing database schema..."

# Load CloudSQL config if exists
if [ -f /tmp/cloudsql-config.sh ]; then
  source /tmp/cloudsql-config.sh
fi

# Prompt for DB password if not set
if [ -z "$DB_PASSWORD" ]; then
  echo "Enter database password:"
  read -s DB_PASSWORD
fi

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
  echo "Error: cloud-sql-proxy not found. Please install it:"
  echo "  brew install cloud-sql-proxy"
  echo "  or"
  echo "  https://cloud.google.com/sql/docs/postgres/sql-proxy"
  exit 1
fi

# Get connection name
if [ -z "$CONNECTION_NAME" ]; then
  CONNECTION_NAME=$(gcloud sql instances describe ${INSTANCE_NAME} \
    --project=${PROJECT_ID} \
    --format="value(connectionName)")
fi

echo "Starting Cloud SQL Proxy..."
cloud-sql-proxy ${CONNECTION_NAME} &
PROXY_PID=$!

# Wait for proxy to start
sleep 5

# Run init script
echo "Running database initialization script..."
PGPASSWORD=${DB_PASSWORD} psql \
  -h 127.0.0.1 \
  -U ${DB_USER} \
  -d ${DB_NAME} \
  -f init-db.sql

# Stop proxy
echo "Stopping Cloud SQL Proxy..."
kill ${PROXY_PID}

echo ""
echo "Database schema initialized successfully!"
