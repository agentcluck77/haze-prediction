#!/bin/bash
set -e

IMAGE_NAME=${1:-"hacx-vit-classifier"}
TAG=${2:-"latest"}

echo "Building Docker image: ${IMAGE_NAME}:${TAG}"
docker build -t "${IMAGE_NAME}:${TAG}" .
echo "Docker image built successfully: ${IMAGE_NAME}:${TAG}"