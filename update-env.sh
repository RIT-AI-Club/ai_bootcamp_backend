#!/bin/bash

# Helper script to update environment variables in Cloud Run
# Usage: ./update-env.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load config from .env.production
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠${NC} Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
set -a
source "$ENV_FILE"
set +a

echo -e "${BLUE}==>${NC} Updating Cloud Run environment variables..."
echo ""
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "Project: ${PROJECT_ID}"
echo ""

# Prompt for DATABASE_URL if needed
if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"CHANGE_ME"* ]]; then
    echo -e "${YELLOW}⚠${NC} DATABASE_URL not set or contains placeholder"
    read -p "Enter DATABASE_URL: " DATABASE_URL
fi

echo ""
echo -e "${BLUE}==>${NC} Updating environment variables..."

gcloud run services update "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
    --set-env-vars="JWT_SECRET_KEY=${JWT_SECRET_KEY}" \
    --set-env-vars="JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}" \
    --set-env-vars="SESSION_SECRET_KEY=${SESSION_SECRET_KEY}" \
    --set-env-vars="CORS_ORIGINS=${CORS_ORIGINS}" \
    --set-env-vars="ENVIRONMENT=production" \
    --set-env-vars="JWT_ALGORITHM=HS256" \
    --set-env-vars="ACCESS_TOKEN_EXPIRE_MINUTES=60" \
    --set-env-vars="REFRESH_TOKEN_EXPIRE_DAYS=7"

echo ""
echo -e "${GREEN}✓${NC} Environment variables updated successfully!"
echo ""
echo "View service:"
echo "  gcloud run services describe ${SERVICE_NAME} --region=${REGION}"
