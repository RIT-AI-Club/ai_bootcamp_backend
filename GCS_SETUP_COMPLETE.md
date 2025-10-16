# Google Cloud Storage Setup - COMPLETE ✅

**Date:** 2025-10-16
**Project:** ai-bootcamp-475320

---

## ✅ What Was Configured

### 1. GCS Bucket Created
- **Bucket Name:** `aibc-submissions`
- **Location:** `us-central1` (same region as Cloud Run)
- **Storage Class:** STANDARD
- **Access Control:** Uniform bucket-level access
- **Soft Delete:** 7-day retention (default)
- **URL:** `gs://aibc-submissions/`

### 2. Service Account Created
- **Name:** `aibc-backend-gcs`
- **Email:** `aibc-backend-gcs@ai-bootcamp-475320.iam.gserviceaccount.com`
- **Display Name:** "AIBC Backend GCS"

### 3. IAM Permissions Granted
- ✅ `roles/storage.objectCreator` - Can upload files to bucket
- ✅ `roles/storage.objectViewer` - Can read files and generate signed URLs

### 4. Service Account Key Generated
- **Location:** `aibc_auth/gcs-key.json`
- **Key ID:** `8f2cee2eae2ce4d887ac21e3e92406b32ee72040`
- **Type:** JSON key file
- **Permissions:** `600` (read-only for owner)

### 5. Environment Configuration Updated
- ✅ `.env` already has correct project ID: `ai-bootcamp-475320`
- ✅ `.env` has correct bucket name: `aibc-submissions`
- ✅ `.env` has correct key path: `/app/gcs-key.json`

### 6. Git Ignore Updated
- ✅ Added `gcs-key.json` to `.gitignore`
- ✅ Added `**/gcs-key.json` to prevent accidental commits

---

## 🔒 Security Notes

1. **Service Account Key** - Stored locally in `aibc_auth/gcs-key.json`
   - ⚠️ **NEVER commit this file to git** (already in .gitignore)
   - File permissions: `600` (owner read-only)

2. **Minimal Permissions** - Service account only has:
   - Storage Object Creator (write files)
   - Storage Object Viewer (read files)
   - No admin or deletion permissions

3. **Bucket Access** - Uniform bucket-level access enabled
   - Access controlled via IAM only
   - No legacy ACLs

---

## 📁 File Upload Structure

Files will be uploaded to:
```
gs://aibc-submissions/
├── pathways/
│   ├── image-generation/
│   │   ├── users/
│   │   │   ├── {user_uuid}/
│   │   │   │   ├── resources/
│   │   │   │   │   ├── {resource_id}/
│   │   │   │   │   │   ├── 2025-10-16_14-30-00_filename.png
│   ├── prompt-engineering/
│   │   ├── users/...
```

---

## 🧪 Testing GCS Integration

Once the migration is run and services are started, you can test:

```bash
# 1. Check if backend can access GCS
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/health

# 2. Upload a test file
curl -X POST \
  -H "Authorization: Bearer {token}" \
  -F "file=@test_image.png" \
  http://localhost:8000/api/v1/resources/users/me/resources/foundations-image-gen-r3/upload

# 3. List user submissions
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/resources/users/me/resources/foundations-image-gen-r3/submissions

# 4. Get signed download URL
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/resources/users/me/submissions/download/{submission_id}
```

---

## 🚀 Next Steps

### 1. Run Database Migration
```bash
docker exec -i aibc_postgres psql -U postgres -d aibc_db < migrations/001_add_resource_tracking.sql
```

### 2. Rebuild Auth Service (to install google-cloud-storage)
```bash
docker-compose build auth_service
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Verify GCS Integration
```bash
# Check logs for GCS manager initialization
docker logs aibc_auth | grep "GCS Manager"

# Should see:
# INFO - GCS Manager initialized for bucket: aibc-submissions
```

---

## 📊 Cost Estimation

**For 60 users with ~50 MB average uploads:**
- **Storage:** 3 GB × $0.02/GB/month = **$0.06/month**
- **Operations:** 1,200 uploads/month × $0.005/1,000 = **$0.01/month**
- **Egress:** Minimal (signed URLs) = **~$0.00/month**

**Total GCS Cost: ~$0.07/month** (essentially free)

---

## 🔧 Troubleshooting

### If uploads fail with authentication errors:

1. **Check key file exists:**
   ```bash
   ls -l aibc_auth/gcs-key.json
   ```

2. **Verify service account permissions:**
   ```bash
   gcloud projects get-iam-policy ai-bootcamp-475320 \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:aibc-backend-gcs@ai-bootcamp-475320.iam.gserviceaccount.com"
   ```

3. **Test GCS access directly:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/home/roman/ai_bootcamp_backend/aibc_auth/gcs-key.json
   echo "test" | gcloud storage cp - gs://aibc-submissions/test.txt
   gcloud storage rm gs://aibc-submissions/test.txt
   ```

---

## ✅ Checklist

- [x] GCS bucket created (`aibc-submissions`)
- [x] Service account created (`aibc-backend-gcs`)
- [x] IAM permissions granted (Storage Object Creator + Viewer)
- [x] Service account key generated (`gcs-key.json`)
- [x] `.env` configured with correct values
- [x] `.gitignore` updated to exclude key file
- [ ] Database migration run
- [ ] Auth service rebuilt with google-cloud-storage
- [ ] Services started and tested

---

**GCS Setup Status: ✅ COMPLETE**

The Google Cloud Storage bucket is fully configured and ready to receive file uploads from the AI Bootcamp backend!
