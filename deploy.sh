#!/bin/bash

# AI Bootcamp Backend - Simple Cloud Run Deployment Script
# This script handles everything: Docker build, push, and Terraform deploy
#
# Usage:
#   ./deploy.sh                    # Full deployment with env vars
#   ./deploy.sh --skip-env-update  # Only update image, keep existing env vars

set -e

# Parse arguments
SKIP_ENV_UPDATE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-env-update)
            SKIP_ENV_UPDATE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./deploy.sh [--skip-env-update]"
            exit 1
            ;;
    esac
done

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"

# Print with color
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  AI Bootcamp Backend - Cloud Run Deployment             ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Load environment variables from .env.production
load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_warning "Please create .env.production with your configuration"
        exit 1
    fi

    print_status "Loading environment variables from ${ENV_FILE}..."

    # Export variables from .env file
    set -a
    source "$ENV_FILE"
    set +a

    # Validate required variables (DATABASE_URL will be set manually in Cloud Run)
    REQUIRED_VARS=(
        "PROJECT_ID"
        "REGION"
        "SERVICE_NAME"
        "JWT_SECRET_KEY"
        "JWT_REFRESH_SECRET_KEY"
        "SESSION_SECRET_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required variable $var is not set in $ENV_FILE"
            exit 1
        fi
    done

    # Warn about DATABASE_URL if it contains placeholder text
    if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"CHANGE_ME"* ]] || [[ "$DATABASE_URL" == *"PROJECT:REGION:INSTANCE"* ]]; then
        print_warning "DATABASE_URL appears to have placeholder values"
        print_warning "Remember to update DATABASE_URL in Cloud Run console after deployment"
    fi

    print_success "Environment variables loaded"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    print_success "Docker found"

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed or not in PATH"
        exit 1
    fi
    print_success "gcloud CLI found"

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed or not in PATH"
        exit 1
    fi
    print_success "Terraform found"

    # Verify gcloud authentication
    print_status "Verifying gcloud authentication..."
    if ! gcloud auth print-access-token &> /dev/null; then
        print_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    print_success "gcloud authenticated"

    # Set gcloud project
    print_status "Setting gcloud project to ${PROJECT_ID}..."
    gcloud config set project "${PROJECT_ID}" --quiet
    print_success "Project set"
}

# Build Docker image
build_image() {
    print_status "Building Docker image..."

    IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    IMAGE_TAG="${IMAGE_NAME}:${TIMESTAMP}"
    IMAGE_LATEST="${IMAGE_NAME}:latest"

    echo ""
    print_status "Image tag: ${IMAGE_TAG}"
    print_status "Building from: ${SCRIPT_DIR}/aibc_auth"
    echo ""

    # Build the image
    docker build \
        -t "${IMAGE_TAG}" \
        -t "${IMAGE_LATEST}" \
        -f "${SCRIPT_DIR}/aibc_auth/Dockerfile" \
        "${SCRIPT_DIR}/aibc_auth"

    print_success "Docker image built successfully"
}

# Setup Artifact Registry
setup_artifact_registry() {
    print_status "Setting up Artifact Registry..."

    # Ensure Artifact Registry API is enabled
    print_status "Checking Artifact Registry API..."
    if ! gcloud services list --enabled --project="${PROJECT_ID}" --filter="name:artifactregistry.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "artifactregistry"; then
        print_status "Enabling Artifact Registry API..."
        gcloud services enable artifactregistry.googleapis.com --project="${PROJECT_ID}"
        sleep 5  # Wait for API to be fully enabled
    fi

    # Check if repository exists with timeout
    print_status "Checking for existing repository..."
    if timeout 30 gcloud artifacts repositories describe "${SERVICE_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" &> /dev/null; then
        print_success "Artifact Registry repository already exists"
    else
        print_status "Creating Artifact Registry repository..."
        gcloud artifacts repositories create "${SERVICE_NAME}" \
            --repository-format=docker \
            --location="${REGION}" \
            --description="AI Bootcamp Auth Service images" \
            --project="${PROJECT_ID}"
        print_success "Artifact Registry repository created"
    fi

    # Configure Docker authentication
    print_status "Configuring Docker authentication..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
    print_success "Docker authentication configured"
}

# Push Docker image
push_image() {
    print_status "Pushing Docker image to Artifact Registry..."

    echo ""
    print_status "Pushing: ${IMAGE_TAG}"
    docker push "${IMAGE_TAG}"

    print_status "Pushing: ${IMAGE_LATEST}"
    docker push "${IMAGE_LATEST}"

    print_success "Docker image pushed successfully"
}

# Deploy with Terraform
deploy_terraform() {
    print_status "Deploying with Terraform..."

    cd "${SCRIPT_DIR}/terraform"

    # Unset GOOGLE_APPLICATION_CREDENTIALS for local Terraform (use gcloud ADC instead)
    unset GOOGLE_APPLICATION_CREDENTIALS

    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -upgrade

    # Create terraform.tfvars
    print_status "Creating terraform.tfvars..."

    if [ "$SKIP_ENV_UPDATE" = true ]; then
        print_warning "Skipping environment variable updates (--skip-env-update flag set)"
        print_warning "Only updating image. Existing env vars in Cloud Run will be preserved."
        cat > terraform.tfvars <<EOF
project_id              = "${PROJECT_ID}"
region                  = "${REGION}"
service_name            = "${SERVICE_NAME}"
image_url               = "${IMAGE_TAG}"
database_url            = "placeholder-will-be-ignored"
jwt_secret_key          = "placeholder-will-be-ignored"
jwt_refresh_secret_key  = "placeholder-will-be-ignored"
session_secret_key      = "placeholder-will-be-ignored"
cors_origins            = "placeholder-will-be-ignored"
google_client_id        = ""
google_client_secret    = ""
min_instances           = ${MIN_INSTANCES:-1}
max_instances           = ${MAX_INSTANCES:-10}
cpu                     = "${CPU:-1}"
memory                  = "${MEMORY:-512Mi}"
allow_unauthenticated   = ${ALLOW_UNAUTHENTICATED:-true}
EOF
    else
        cat > terraform.tfvars <<EOF
project_id              = "${PROJECT_ID}"
region                  = "${REGION}"
service_name            = "${SERVICE_NAME}"
image_url               = "${IMAGE_TAG}"
database_url            = "${DATABASE_URL}"
jwt_secret_key          = "${JWT_SECRET_KEY}"
jwt_refresh_secret_key  = "${JWT_REFRESH_SECRET_KEY}"
session_secret_key      = "${SESSION_SECRET_KEY}"
cors_origins            = "${CORS_ORIGINS:-https://yourdomain.com}"
google_client_id        = "${GOOGLE_CLIENT_ID:-}"
google_client_secret    = "${GOOGLE_CLIENT_SECRET:-}"
min_instances           = ${MIN_INSTANCES:-1}
max_instances           = ${MAX_INSTANCES:-10}
cpu                     = "${CPU:-1}"
memory                  = "${MEMORY:-512Mi}"
allow_unauthenticated   = ${ALLOW_UNAUTHENTICATED:-true}
EOF
    fi

    # Plan
    print_status "Planning Terraform changes..."
    terraform plan -out=tfplan

    # Apply
    print_status "Applying Terraform changes..."
    terraform apply -auto-approve tfplan

    # Get outputs
    print_success "Deployment completed!"
    echo ""
    print_status "Service Information:"
    terraform output -json | jq -r 'to_entries[] | "  \(.key): \(.value.value)"'

    cd "${SCRIPT_DIR}"
}

# Test deployment
test_deployment() {
    print_status "Testing deployment..."

    SERVICE_URL=$(cd "${SCRIPT_DIR}/terraform" && terraform output -raw service_url)

    print_status "Testing health endpoint: ${SERVICE_URL}/health"

    sleep 5  # Wait for service to be ready

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health")

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Health check passed! Service is running."
    else
        print_warning "Health check returned: ${HTTP_CODE}"
        print_warning "Service may still be starting up..."
    fi

    echo ""
    print_success "Deployment complete! Service URL:"
    echo -e "${GREEN}${SERVICE_URL}${NC}"
    echo ""
    print_status "API Documentation: ${SERVICE_URL}/docs"
    echo ""
}

# Main deployment flow
main() {
    print_header

    # Load environment variables
    load_env

    # Check prerequisites
    check_prerequisites

    # Setup Artifact Registry
    setup_artifact_registry

    # Build Docker image
    build_image

    # Push Docker image
    push_image

    # Deploy with Terraform
    deploy_terraform

    # Test deployment
    test_deployment

    print_success "All done! 🚀"
}

# Run main function
main "$@"
