# GCS Credentials Secret Setup for Cloud Run

This guide shows how to securely mount your GCS service account key in Cloud Run.

## What Was Done Automatically

The deployment script now automatically handles the secret mounting via Terraform. However, if you need to manually configure or troubleshoot, use this guide.

## One-Time Setup (Already Completed)

### 1. Create Secret in Secret Manager
```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=ai-bootcamp-475320

# Create secret from your gcs-key.json file
gcloud secrets create gcp-key \
  --data-file=/home/roman/ai_bootcamp_backend/aibc_auth/gcs-key.json \
  --project=ai-bootcamp-475320
```

### 2. Grant Cloud Run Access to Secret
```bash
# Grant the default compute service account access to the secret
gcloud secrets add-iam-policy-binding gcp-key \
  --member=serviceAccount:778590086943-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=ai-bootcamp-475320
```

## Terraform Configuration (Already Set Up)

The Terraform configuration (`terraform/main.tf`) includes:

### Volume Mount in Container
```hcl
containers {
  # ... other config ...

  volume_mounts {
    name       = "gcp-key-volume"
    mount_path = "/secrets"
  }
}
```

### Volume Definition
```hcl
volumes {
  name = "gcp-key-volume"
  secret {
    secret       = "gcp-key"
    default_mode = 292  # 0444 in decimal (read-only)
    items {
      version = "latest"
      path    = "gcp-key.json"
    }
  }
}
```

### Environment Variable
```bash
GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json
```

The secret will be available at: `/secrets/gcp-key.json` inside the container.

## Manual YAML Configuration (For Console Deployment)

If you need to deploy via Google Cloud Console manually, copy this YAML section:

### Copy-Paste YAML Section

```yaml
spec:
  template:
    spec:
      containers:
      - image: YOUR_IMAGE_URL
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /secrets/gcp-key.json
        # ... other env vars ...

        volumeMounts:
        - name: gcp-key-volume
          mountPath: /secrets
          readOnly: true

        resources:
          limits:
            cpu: '1'
            memory: 512Mi

      volumes:
      - name: gcp-key-volume
        secret:
          secretName: gcp-key
          items:
          - key: latest
            path: gcp-key.json
          defaultMode: 292  # 0444 (read-only)
```

## Verification

After deployment, you can verify the secret is mounted:

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe aibc-auth-service \
  --region=us-east1 \
  --project=ai-bootcamp-475320 \
  --format='value(status.url)')

# Check if the service can access GCS (test endpoint needed)
curl $SERVICE_URL/health
```

## Troubleshooting

### Secret not found error
```bash
# Verify secret exists
gcloud secrets describe gcp-key --project=ai-bootcamp-475320

# Verify IAM permissions
gcloud secrets get-iam-policy gcp-key --project=ai-bootcamp-475320
```

### Permission denied
```bash
# Re-grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding gcp-key \
  --member=serviceAccount:778590086943-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=ai-bootcamp-475320
```

### Update secret value
```bash
# Add a new version of the secret
gcloud secrets versions add gcp-key \
  --data-file=/path/to/new/gcs-key.json \
  --project=ai-bootcamp-475320

# Redeploy service to use new version
./deploy.sh
```

## Security Best Practices

✅ **What we're doing right:**
- Secret stored in Secret Manager (not in code or env vars)
- Read-only mount (mode 0444)
- IAM-based access control
- Secret never exposed in logs or code

⚠️ **Important:**
- Never commit `gcs-key.json` to git (it's in `.gitignore`)
- Rotate keys periodically
- Use least-privilege IAM roles for the service account

## Files Modified

- `terraform/main.tf` - Added volume mount and volume definition
- `.env.production` - Updated `GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json`
- Secret created: `projects/ai-bootcamp-475320/secrets/gcp-key`

## Deploy

Now just run:
```bash
./deploy.sh
```

The secret will be automatically mounted at `/secrets/gcp-key.json` in your Cloud Run container!
