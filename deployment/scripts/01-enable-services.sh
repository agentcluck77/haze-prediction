#!/bin/bash
# Enable required GCP services

set -e

PROJECT_ID="hacx-477608"

echo "Enabling required GCP services for project: ${PROJECT_ID}"

gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  compute.googleapis.com \
  --project=${PROJECT_ID}

echo "All services enabled successfully!"
