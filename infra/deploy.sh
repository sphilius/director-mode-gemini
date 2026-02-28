#!/usr/bin/env bash
# Director Mode — Deployment script
# Usage: ./infra/deploy.sh [project-id] [region]

set -euo pipefail

PROJECT_ID="${1:-director-mode}"
REGION="${2:-us-central1}"
IMAGE="gcr.io/${PROJECT_ID}/director-mode"
SERVICE_NAME="director-mode"

echo "==> Building Docker image…"
docker build -t "${IMAGE}:latest" .

echo "==> Pushing to Container Registry…"
docker push "${IMAGE}:latest"

echo "==> Deploying to Cloud Run…"
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}:latest" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY:-}" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --port 8000

echo "==> Deployment complete!"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format "value(status.url)"
