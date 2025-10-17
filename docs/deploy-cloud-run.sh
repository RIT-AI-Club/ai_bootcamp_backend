#!/bin/bash

# Manual deployment script for Google Cloud Run
# Use this for quick manual deployments without Cloud Build

set -e

# Configuration - UPDATE THESE VALUES
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
SERVICE_NAME="aibc-auth-service"
IMAGE_NAME="aibc-auth"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AI Bootcamp Auth Service - Cloud Run Deployment ===${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "gcloud CLI not found. Please install it first."
    exit 1
fi

# Set project
echo -e "${BLUE}Setting GCP project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Build the Docker image
echo -e "${BLUE}Building Docker image...${NC}"
cd aibc_auth
docker build -t gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest .
cd ..

# Push to Container Registry
echo -e "${BLUE}Pushing image to Container Registry...${NC}"
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo -e "${BLUE}Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 10 \
  --cpu 1 \
  --memory 512Mi \
  --concurrency 80 \
  --timeout 60 \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_URL=DATABASE_URL:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,JWT_REFRESH_SECRET_KEY=JWT_REFRESH_SECRET_KEY:latest

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}Service URL:${NC}"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
