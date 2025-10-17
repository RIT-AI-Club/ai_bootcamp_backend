# AI Bootcamp Backend - Cloud Run Deployment Guide

Simple, automated deployment to Google Cloud Run using Terraform and Docker.

## Prerequisites

Before deploying, ensure you have:

1. **Docker Desktop** installed and running
2. **Google Cloud CLI (gcloud)** installed and authenticated
3. **Terraform** installed (>= 1.0)
4. **A GCP project** with billing enabled
5. **Cloud SQL PostgreSQL instance** (or external PostgreSQL database)

### Quick Install Commands

```bash
# Install gcloud CLI (macOS)
brew install google-cloud-sdk

# Install Terraform (macOS)
brew install terraform

# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

## Quick Start (3 Steps)

### Step 1: Configure Environment Variables

Copy the template and fill in your values:

```bash
cp .env.production.template .env.production
```

Edit `.env.production` with your configuration:

```bash
# REQUIRED: Update these values
PROJECT_ID=your-gcp-project-id
REGION=us-central1
DATABASE_URL=postgresql://user:pass@host/db
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_REFRESH_SECRET_KEY=$(openssl rand -hex 32)
SESSION_SECRET_KEY=$(openssl rand -hex 32)

# OPTIONAL: Configure as needed
CORS_ORIGINS=https://yourdomain.com
MIN_INSTANCES=1
MAX_INSTANCES=10
```

### Step 2: Enable Required GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com
```

### Step 3: Deploy

```bash
./deploy.sh
```

That's it! The script will:
- ✅ Build the Docker image locally
- ✅ Create Artifact Registry repository (if needed)
- ✅ Push image to Artifact Registry
- ✅ Deploy to Cloud Run with Terraform
- ✅ Configure all environment variables
- ✅ Test the deployment
- ✅ Output the service URL

## What the Deployment Does

### Docker Build
- Builds optimized production image from `aibc_auth/Dockerfile`
- Uses non-root user for security
- Configures Cloud Run-specific settings (port 8080)
- Tags with timestamp and 'latest'

### Artifact Registry
- Creates Docker repository in your region
- Configures Docker authentication automatically
- Pushes tagged images

### Terraform Deployment
- Creates Cloud Run service with optimal settings
- Configures auto-scaling (1-10 instances)
- Sets up health checks and probes
- Injects environment variables securely
- Enables public access (configurable)

### Configuration Applied
- **CPU:** 1 vCPU per instance
- **Memory:** 512Mi per instance
- **Concurrency:** 80 requests per instance
- **Timeout:** 60 seconds
- **Min Instances:** 1 (no cold starts)
- **Max Instances:** 10 (handles 60+ users)

## Deployment Output

After successful deployment, you'll see:

```
╔═══════════════════════════════════════════════════════════╗
║  AI Bootcamp Backend - Cloud Run Deployment              ║
╚═══════════════════════════════════════════════════════════╝

✓ Environment variables loaded
✓ Docker found
✓ gcloud CLI found
✓ Terraform found
✓ gcloud authenticated
✓ Docker image built successfully
✓ Docker image pushed successfully
✓ Deployment completed!

Service Information:
  service_url: https://aibc-auth-service-xxxxx-uc.a.run.app
  service_name: aibc-auth-service
  service_location: us-central1

✓ Health check passed! Service is running.

Deployment complete! Service URL:
https://aibc-auth-service-xxxxx-uc.a.run.app

API Documentation: https://aibc-auth-service-xxxxx-uc.a.run.app/docs

All done! 🚀
```

## Testing Your Deployment

### Health Check
```bash
curl https://your-service-url.run.app/health
```

### API Documentation
Visit: `https://your-service-url.run.app/docs`

### Test Authentication
```bash
# Sign up
curl -X POST "https://your-service-url.run.app/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "SecurePass123!"
  }'

# Login
curl -X POST "https://your-service-url.run.app/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=test@example.com&password=SecurePass123!'
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ID` | GCP Project ID | `my-project-123` |
| `REGION` | GCP Region | `us-central1` |
| `SERVICE_NAME` | Cloud Run service name | `aibc-auth-service` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `JWT_SECRET_KEY` | Access token secret | Generate with `openssl rand -hex 32` |
| `JWT_REFRESH_SECRET_KEY` | Refresh token secret | Generate with `openssl rand -hex 32` |
| `SESSION_SECRET_KEY` | Session secret | Generate with `openssl rand -hex 32` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `https://yourdomain.com` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | (empty) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret | (empty) |
| `MIN_INSTANCES` | Minimum Cloud Run instances | `1` |
| `MAX_INSTANCES` | Maximum Cloud Run instances | `10` |
| `CPU` | CPU per instance | `1` |
| `MEMORY` | Memory per instance | `512Mi` |
| `ALLOW_UNAUTHENTICATED` | Public access | `true` |

## Cloud SQL Setup

If you need to create a Cloud SQL PostgreSQL instance:

```bash
# Create Cloud SQL instance
gcloud sql instances create aibc-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Set root password
gcloud sql users set-password postgres \
  --instance=aibc-postgres \
  --password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create aibc_db --instance=aibc-postgres

# Create user
gcloud sql users create aibc_admin \
  --instance=aibc-postgres \
  --password=YOUR_SECURE_PASSWORD

# Get connection name
gcloud sql instances describe aibc-postgres --format='value(connectionName)'
# Use this in DATABASE_URL: /cloudsql/CONNECTION_NAME
```

Then update your `DATABASE_URL` in `.env.production`:

```bash
DATABASE_URL=postgresql://aibc_admin:PASSWORD@/aibc_db?host=/cloudsql/PROJECT:REGION:INSTANCE&sslmode=disable
```

## Updating the Deployment

To update your service after making code changes:

```bash
./deploy.sh
```

The script automatically:
- Rebuilds the Docker image
- Tags with new timestamp
- Deploys the new version
- Terraform handles the rollout

## Monitoring & Logs

### View Logs
```bash
# Cloud Run logs
gcloud run services logs read aibc-auth-service --region=us-central1

# Follow logs in real-time
gcloud run services logs tail aibc-auth-service --region=us-central1
```

### View Service Details
```bash
gcloud run services describe aibc-auth-service --region=us-central1
```

### View Metrics
Visit Cloud Console: https://console.cloud.google.com/run

## Manual Terraform Commands

If you need to run Terraform manually:

```bash
cd terraform

# Initialize
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy
```

## Troubleshooting

### Docker Build Fails
```bash
# Check Docker is running
docker ps

# Clean Docker cache
docker system prune -a
```

### Authentication Issues
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Deployment Fails
```bash
# Check service status
gcloud run services describe aibc-auth-service --region=us-central1

# View recent logs
gcloud run services logs read aibc-auth-service --limit=50
```

### Database Connection Issues
- Ensure Cloud SQL instance is running
- Verify connection string format
- Check firewall rules
- Enable Cloud SQL Admin API

## Cost Estimation

For 60 active users:

| Resource | Configuration | Monthly Cost |
|----------|---------------|--------------|
| Cloud Run | 1-2 instances, 512Mi RAM | $15-20 |
| Cloud SQL | db-f1-micro PostgreSQL | $7-10 |
| Artifact Registry | <10GB storage | <$1 |
| **Total** | | **~$23-31/month** |

## Security Best Practices

✅ **Implemented:**
- Non-root container user
- Environment variables for secrets
- HTTPS-only (enforced by Cloud Run)
- JWT token authentication
- Password hashing with bcrypt
- Rate limiting
- Account lockout protection
- Audit logging

🔒 **Recommended:**
- Enable Cloud Armor for DDoS protection
- Use Secret Manager instead of env vars (optional)
- Enable VPC for private Cloud SQL connection
- Set up Cloud Monitoring alerts
- Regular security updates

## Next Steps

1. **Set up Cloud SQL** (if not done)
2. **Configure custom domain** (Cloud Run domain mapping)
3. **Set up CI/CD** (Cloud Build, GitHub Actions)
4. **Enable monitoring** (Cloud Monitoring alerts)
5. **Configure frontend** (update API endpoint)

## Support & Documentation

- **Cloud Run Docs:** https://cloud.google.com/run/docs
- **Terraform Google Provider:** https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com

## Files Reference

```
.
├── deploy.sh                      # Main deployment script
├── .env.production.template       # Environment template
├── .env.production               # Your config (gitignored)
├── aibc_auth/
│   ├── Dockerfile                # Production-optimized Docker image
│   └── app/                      # FastAPI application
└── terraform/
    ├── main.tf                   # Cloud Run infrastructure
    ├── variables.tf              # Configuration variables
    ├── outputs.tf                # Deployment outputs
    └── .gitignore               # Ignore sensitive files
```

---

**Ready to deploy?** Just run `./deploy.sh` and you're live in minutes! 🚀
