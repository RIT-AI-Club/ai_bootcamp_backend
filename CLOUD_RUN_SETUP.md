# Google Cloud Run Deployment Guide

## Prerequisites

1. **Google Cloud Project**
   ```bash
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

3. **Install Google Cloud SDK**
   - Download from: https://cloud.google.com/sdk/docs/install

---

## Step 1: Set Up Cloud SQL (PostgreSQL)

### Create Cloud SQL Instance
```bash
gcloud sql instances create aibc-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=CHANGE_THIS_PASSWORD \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup-start-time=03:00
```

**Cost Optimization for 60 users:**
- `db-f1-micro`: Cheapest tier (~$7.67/month)
- Shared CPU, 0.6GB RAM
- Perfect for 60 users with your workload

**For better performance** (if budget allows):
```bash
--tier=db-g1-small  # ~$26/month, 1.7GB RAM, better for production
```

### Create Database and User
```bash
gcloud sql databases create aibc_db --instance=aibc-postgres

gcloud sql users create aibc_admin \
  --instance=aibc-postgres \
  --password=YOUR_SECURE_PASSWORD
```

### Run Database Initialization
```bash
# Connect to Cloud SQL
gcloud sql connect aibc-postgres --user=postgres

# In PostgreSQL shell:
\c aibc_db
# Paste contents of init-complete.sql
# Or upload via Cloud Console
```

---

## Step 2: Store Secrets in Secret Manager

```bash
# Database URL
echo -n "postgresql://aibc_admin:YOUR_PASSWORD@/aibc_db?host=/cloudsql/PROJECT_ID:us-central1:aibc-postgres" | \
  gcloud secrets create DATABASE_URL --data-file=-

# JWT Secret Keys (generate strong random keys)
openssl rand -base64 32 | gcloud secrets create JWT_SECRET_KEY --data-file=-
openssl rand -base64 32 | gcloud secrets create JWT_REFRESH_SECRET_KEY --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding JWT_SECRET_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding JWT_REFRESH_SECRET_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 3: Deploy to Cloud Run

### Option A: Automated with Cloud Build
```bash
# Trigger Cloud Build from repository
gcloud builds submit --config=cloudbuild.yaml
```

### Option B: Manual Deployment
```bash
# Edit deploy-cloud-run.sh with your PROJECT_ID
chmod +x deploy-cloud-run.sh
./deploy-cloud-run.sh
```

### Option C: Direct gcloud Command
```bash
# Build and push
cd aibc_auth
docker build -t gcr.io/YOUR_PROJECT_ID/aibc-auth:latest .
docker push gcr.io/YOUR_PROJECT_ID/aibc-auth:latest

# Deploy
gcloud run deploy aibc-auth-service \
  --image gcr.io/YOUR_PROJECT_ID/aibc-auth:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:aibc-postgres \
  --min-instances 1 \
  --max-instances 10 \
  --cpu 1 \
  --memory 512Mi \
  --concurrency 80 \
  --timeout 60 \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_URL=DATABASE_URL:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,JWT_REFRESH_SECRET_KEY=JWT_REFRESH_SECRET_KEY:latest
```

---

## Step 4: Update Frontend CORS

After deployment, get your Cloud Run URL:
```bash
gcloud run services describe aibc-auth-service --region us-central1 --format 'value(status.url)'
```

Update your frontend to call this URL instead of `localhost:8000`.

---

## Cost Optimization Summary

### For 60 Users - Estimated Monthly Costs:

1. **Cloud SQL (db-f1-micro)**: ~$7.67/month
2. **Cloud Run**:
   - 1 min instance always running: ~$8.50/month (180 hours)
   - Additional instances scale to 0
   - 512MB RAM, 1 vCPU per instance
   - Estimated: ~$10-15/month for 60 users

**Total: ~$18-23/month**

### Cost Optimization Tips:

1. **Use Cloud SQL Proxy** (already configured in code)
   - Reduces connection overhead
   - Better connection pooling

2. **Keep min-instances=1**
   - Eliminates cold starts
   - Only ~$8.50/month for always-on instance
   - Worth it for user experience

3. **Set concurrency=80**
   - Each instance handles 80 concurrent requests
   - For 60 users: 1-2 instances max
   - Reduces costs significantly

4. **Enable Cloud SQL automatic backups**
   - Already included in setup
   - Runs at 3 AM daily

5. **Monitor with Cloud Monitoring** (free tier)
   ```bash
   gcloud monitoring dashboards create --config-from-file=dashboard.json
   ```

---

## Performance Optimizations (Already Applied)

### 1. Database Connection Pooling
- **Local**: pool_size=5, max_overflow=10
- **Cloud Run**: pool_size=2, max_overflow=3
- Auto-detects Cloud Run via `K_SERVICE` env var

### 2. Async Password Hashing
- bcrypt runs in thread pool (non-blocking)
- Prevents event loop blocking
- Faster response times

### 3. Optimized bcrypt Rounds
- **Local**: 12 rounds (~250ms)
- **Cloud Run**: 10 rounds (~100ms)
- Still highly secure

### 4. Structured JSON Logging
- Auto-formatted for Cloud Logging
- Better log analysis and filtering
- No extra setup needed

### 5. Fast Container Startup
- Lightweight `python:3.11-slim` base
- Optimized layer caching
- Health checks configured

---

## Monitoring & Scaling

### View Logs
```bash
gcloud run services logs read aibc-auth-service --region us-central1 --limit 50
```

### Check Metrics
```bash
gcloud run services describe aibc-auth-service --region us-central1
```

### Auto-Scaling Configuration
- **Min instances**: 1 (always warm)
- **Max instances**: 10 (handles 800 concurrent requests)
- **Concurrency**: 80 requests per instance
- **CPU**: 1 vCPU per instance
- **Memory**: 512Mi per instance

**For 60 users**: You'll typically use 1-2 instances max.

### Scaling Math
- 60 users × ~2 requests/second = 120 RPS peak
- 80 concurrency × 2 instances = 160 concurrent capacity
- **Result**: Plenty of headroom!

---

## Security Checklist

- [x] Secrets stored in Secret Manager (not in code)
- [x] Cloud SQL with private IP recommended
- [x] JWT tokens with secure random keys
- [x] Rate limiting enabled (slowapi)
- [x] Account lockout after 5 failed attempts
- [x] bcrypt password hashing
- [x] CORS configured for frontend origin
- [ ] Add Cloud Armor for DDoS protection (optional)
- [ ] Enable Cloud SQL SSL connections (recommended)
- [ ] Set up Cloud IAP for admin access (optional)

---

## Troubleshooting

### Container fails to start
```bash
gcloud run services logs read aibc-auth-service --region us-central1 --limit 100
```

### Database connection issues
- Check Cloud SQL connection name
- Verify secrets are set correctly
- Ensure Cloud Run service account has Cloud SQL client role

### Cold starts too slow
- Increase `min-instances` to 2 or more
- Optimize Dockerfile layer caching
- Consider Cloud Run Gen 2 execution environment

---

## Next Steps After Deployment

1. **Set up CI/CD** with Cloud Build triggers
2. **Configure custom domain** with Cloud Run
3. **Enable Cloud CDN** for static assets (if any)
4. **Set up alerts** for errors and high latency
5. **Configure frontend** to use production URL

---

## Support Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cost Calculator](https://cloud.google.com/products/calculator)
