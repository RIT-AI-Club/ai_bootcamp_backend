# Resource-Level Progress Tracking Implementation Plan

**Created:** 2025-10-16
**Status:** Design Phase Complete - Ready for Implementation
**Purpose:** Complete resource-level tracking with file uploads for AI Bootcamp pathways

---

## Problem Statement

The current system only tracks progress at the **pathway** and **module** levels. We need **granular resource-level tracking** to:

1. Track individual resources (videos, articles, exercises, projects, quizzes)
2. Allow users to check off completed resources
3. Support file uploads for exercises and projects → **Google Cloud Storage**
4. Automatically calculate progress at resource → module → pathway levels
5. Enable instructor review of submissions

---

## Solution Overview

### Database Layer
- **3 new tables** with automatic triggers for progress calculation
- **Automatic cascade updates** from resource → module → pathway completion
- **File upload metadata** stored with GCS paths and review status

### API Layer
- **RESTful endpoints** for progress tracking and file uploads
- **GCS integration** for file storage with signed URLs
- **Instructor review system** for submissions

### Data Flow
```
User completes resource
    ↓
resource_completions.status = 'completed'
    ↓
Trigger: Check if all module resources complete
    ↓
module_completions.completed_at = NOW()
    ↓
Trigger: Check if all pathway modules complete
    ↓
user_progress.progress_percentage = 100
```

---

## Database Schema (IMPLEMENTED ✅)

### Table 1: `resources`
Stores all pathway resources (videos, articles, exercises, projects)

**Key columns:**
- `id` - Unique identifier (e.g., "foundations-image-gen-r1")
- `module_id` - Parent module
- `pathway_id` - Parent pathway
- `type` - 'video', 'article', 'exercise', 'project', 'quiz'
- `requires_upload` - Boolean flag for exercises/projects
- `accepted_file_types` - Array of MIME types
- `max_file_size_mb` - Upload limit

### Table 2: `resource_completions`
Tracks user progress on each resource

**Key columns:**
- `user_id` + `resource_id` - Composite unique key
- `status` - 'not_started', 'in_progress', 'completed', 'submitted', 'reviewed'
- `progress_percentage` - 0-100%
- `time_spent_minutes` - Time tracking
- `submission_count` - Number of files uploaded
- `completed_at` - Completion timestamp

### Table 3: `resource_submissions`
Tracks file uploads to Google Cloud Storage

**Key columns:**
- `user_id` + `resource_id` - Links to resource completion
- `file_name`, `file_size_bytes`, `file_type` - File metadata
- `gcs_bucket`, `gcs_path`, `gcs_url` - GCS location
- `submission_status` - 'uploading', 'uploaded', 'approved', 'rejected'
- `reviewed_by`, `reviewed_at`, `review_comments`, `grade` - Instructor review

---

## Automatic Progress Calculation (IMPLEMENTED ✅)

### Trigger 1: Auto-Complete Modules
```sql
CREATE TRIGGER trigger_auto_complete_module
    AFTER INSERT OR UPDATE ON resource_completions
    FOR EACH ROW EXECUTE FUNCTION update_module_completion_on_resource_complete();
```

**Logic:**
- When resource marked as 'completed'/'submitted'/'reviewed'
- Calculate: `completed_resources / total_resources * 100`
- If 100% → Insert into `module_completions`

### Trigger 2: Auto-Update Pathway Progress
```sql
CREATE TRIGGER trigger_auto_update_pathway_progress
    AFTER INSERT OR UPDATE ON module_completions
    FOR EACH ROW EXECUTE FUNCTION update_pathway_progress_on_module_complete();
```

**Logic:**
- When module completed
- Calculate: `completed_modules / total_modules * 100`
- Update `user_progress.progress_percentage`
- If 100% → Set `user_progress.completed_at`

### Trigger 3: Auto-Increment Submission Count
```sql
CREATE TRIGGER trigger_increment_submission_count
    AFTER INSERT ON resource_submissions
    FOR EACH ROW EXECUTE FUNCTION increment_submission_count();
```

**Logic:**
- When file uploaded with status='uploaded'
- Increment `resource_completions.submission_count`
- Update `resource_completions.status = 'submitted'`

---

## API Endpoints (DESIGNED ✅)

### User Progress Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/pathways/{pathway_id}/resources` | Get all resources |
| GET | `/api/v1/users/me/progress/{pathway_id}` | Full progress report |
| GET | `/api/v1/users/me/resources/{resource_id}/progress` | Resource progress |
| POST | `/api/v1/users/me/resources/{resource_id}/start` | Start resource |
| PUT | `/api/v1/users/me/resources/{resource_id}/progress` | Update progress |
| POST | `/api/v1/users/me/resources/{resource_id}/complete` | Complete resource |

### File Upload Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/users/me/resources/{resource_id}/upload` | Upload file to GCS |
| GET | `/api/v1/users/me/resources/{resource_id}/submissions` | List submissions |
| GET | `/api/v1/users/me/submissions/download/{submission_id}` | Get signed URL |
| DELETE | `/api/v1/users/me/submissions/{submission_id}` | Soft delete |

### Instructor Review Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/admin/submissions/pending` | Pending reviews |
| POST | `/api/v1/admin/submissions/{submission_id}/review` | Review/grade |

---

## Google Cloud Storage Setup

### Bucket Configuration
```
Bucket Name: aibc-submissions
Region: us-central1 (same as Cloud Run)
Storage Class: Standard
Access: Uniform (IAM only, no ACLs)
```

### Folder Structure
```
aibc-submissions/
├── pathways/
│   ├── image-generation/
│   │   ├── users/
│   │   │   ├── {user_uuid}/
│   │   │   │   ├── resources/
│   │   │   │   │   ├── {resource_id}/
│   │   │   │   │   │   ├── 2025-10-16_14-30-00_filename.png
```

### Service Account
```
Name: aibc-backend-gcs
Email: aibc-backend-gcs@{project}.iam.gserviceaccount.com
Roles:
  - Storage Object Creator (write files)
  - Storage Object Viewer (read files for signed URLs)
```

### Environment Variables
```bash
# Add to aibc_auth/.env
GCS_BUCKET_NAME=aibc-submissions
GCS_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

---

## Implementation Phases

### ✅ Phase 1: Database Design (COMPLETE)
- [x] Create `resources` table schema
- [x] Create `resource_completions` table schema
- [x] Create `resource_submissions` table schema
- [x] Add automatic triggers for progress calculation
- [x] Add helper functions for progress calculation
- [x] Add indexes for query optimization
- [x] Insert sample data for image-generation pathway
- [x] Insert sample data for prompt-engineering pathway

**File:** `migrations/001_add_resource_tracking.sql`

---

### ✅ Phase 2: API Design (COMPLETE)
- [x] Design RESTful endpoints for progress tracking
- [x] Design file upload API with GCS integration
- [x] Design instructor review endpoints
- [x] Document request/response schemas
- [x] Document security considerations
- [x] Document user flows

**File:** `docs/API_RESOURCE_TRACKING.md`

---

### 🔄 Phase 3: Backend Implementation (NEXT)

#### Step 3.1: SQLAlchemy Models
**File:** `aibc_auth/app/models/resources.py`

```python
# Create SQLAlchemy models for:
- Resource (maps to resources table)
- ResourceCompletion (maps to resource_completions table)
- ResourceSubmission (maps to resource_submissions table)
```

#### Step 3.2: Pydantic Schemas
**File:** `aibc_auth/app/schemas/resources.py`

```python
# Create Pydantic schemas for:
- ResourceBase, ResourceCreate, ResourceResponse
- ResourceCompletionBase, ResourceCompletionCreate, ResourceCompletionUpdate, ResourceCompletionResponse
- ResourceSubmissionBase, ResourceSubmissionCreate, ResourceSubmissionResponse
- UserProgressResponse (with nested modules and resources)
```

#### Step 3.3: CRUD Operations
**File:** `aibc_auth/app/crud/resources.py`

```python
# Create CRUD functions:
- get_resources_by_pathway(pathway_id)
- get_resources_by_module(module_id)
- get_resource_completion(user_id, resource_id)
- create_resource_completion(user_id, resource_id, data)
- update_resource_completion(user_id, resource_id, data)
- get_user_pathway_progress(user_id, pathway_id)
```

**File:** `aibc_auth/app/crud/submissions.py`

```python
# Create CRUD functions:
- create_submission(user_id, resource_id, file_metadata)
- get_submissions_by_resource(user_id, resource_id)
- get_submission_by_id(submission_id)
- delete_submission(submission_id)
- get_pending_submissions(pathway_id, limit, offset)
- update_submission_review(submission_id, review_data)
```

#### Step 3.4: GCS Integration
**File:** `aibc_auth/app/core/gcs.py`

```python
# Create GCS helper functions:
- upload_file_to_gcs(file: UploadFile, path: str) -> str
- generate_signed_url(gcs_path: str, expiration: int) -> str
- delete_file_from_gcs(gcs_path: str) -> bool
- validate_file(file: UploadFile, allowed_types: List[str], max_size_mb: int) -> bool
```

#### Step 3.5: FastAPI Endpoints
**File:** `aibc_auth/app/api/v1/resources.py`

```python
# Implement endpoints:
- GET /pathways/{pathway_id}/resources
- GET /modules/{module_id}/resources
- GET /users/me/progress/{pathway_id}
- GET /users/me/resources/{resource_id}/progress
- POST /users/me/resources/{resource_id}/start
- PUT /users/me/resources/{resource_id}/progress
- POST /users/me/resources/{resource_id}/complete
```

**File:** `aibc_auth/app/api/v1/submissions.py`

```python
# Implement endpoints:
- POST /users/me/resources/{resource_id}/upload
- GET /users/me/resources/{resource_id}/submissions
- GET /users/me/submissions/download/{submission_id}
- DELETE /users/me/submissions/{submission_id}
- GET /admin/submissions/pending
- POST /admin/submissions/{submission_id}/review
```

---

### 📦 Phase 4: Google Cloud Setup (NEXT)

#### Step 4.1: Create GCS Bucket
```bash
# Create bucket
gcloud storage buckets create gs://aibc-submissions \
  --location=us-central1 \
  --uniform-bucket-level-access

# Create folder structure
gsutil -m mkdir gs://aibc-submissions/pathways/
```

#### Step 4.2: Create Service Account
```bash
# Create service account
gcloud iam service-accounts create aibc-backend-gcs \
  --description="Service account for AI Bootcamp file uploads" \
  --display-name="AIBC Backend GCS"

# Grant permissions
gcloud projects add-iam-policy-binding {PROJECT_ID} \
  --member="serviceAccount:aibc-backend-gcs@{PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator"

gcloud projects add-iam-policy-binding {PROJECT_ID} \
  --member="serviceAccount:aibc-backend-gcs@{PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Create key
gcloud iam service-accounts keys create gcs-key.json \
  --iam-account=aibc-backend-gcs@{PROJECT_ID}.iam.gserviceaccount.com
```

#### Step 4.3: Update Environment Variables
```bash
# Add to aibc_auth/.env
GCS_BUCKET_NAME=aibc-submissions
GCS_PROJECT_ID={your-project-id}
GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

#### Step 4.4: Update Docker
```dockerfile
# Add to aibc_auth/Dockerfile
COPY gcs-key.json /app/gcs-key.json
```

---

### 🎨 Phase 5: Frontend Integration (LATER)

#### Step 5.1: Update Pathway Page
- Display resources grouped by module
- Add checkboxes for videos/articles (mark as complete)
- Add upload button for exercises/projects
- Show progress bars at resource/module/pathway levels

#### Step 5.2: Resource Progress Component
```tsx
// components/ResourceProgress.tsx
- Display resource title, type, duration
- Show completion status (not started, in progress, completed)
- For videos/articles: Checkbox to mark complete
- For exercises/projects: Upload button + file list
- Show time spent on resource
```

#### Step 5.3: File Upload Component
```tsx
// components/FileUpload.tsx
- Drag-and-drop file upload
- File type validation
- File size validation
- Upload progress indicator
- Display uploaded files with download links
- Allow re-uploading (for revisions)
```

#### Step 5.4: API Integration
```typescript
// services/resources.ts
- fetchPathwayProgress(pathwayId)
- startResource(resourceId)
- updateResourceProgress(resourceId, data)
- completeResource(resourceId)
- uploadFile(resourceId, file)
- fetchSubmissions(resourceId)
- deleteSubmission(submissionId)
```

---

### ✅ Phase 6: Testing (LATER)

#### Unit Tests
- Test CRUD operations for resources, completions, submissions
- Test GCS upload/download/delete functions
- Test progress calculation functions
- Test file validation

#### Integration Tests
- Test full resource completion flow
- Test file upload to GCS flow
- Test automatic module/pathway completion
- Test instructor review flow

#### End-to-End Tests
- Test user completing a pathway from start to finish
- Test file upload and download
- Test progress calculation at all levels

---

## Migration Script Execution

### Local Development
```bash
# Stop services
docker-compose down

# Run migration
docker-compose up -d postgres
docker exec -i aibc_postgres psql -U postgres -d aibc_db < migrations/001_add_resource_tracking.sql

# Restart services
docker-compose up -d
```

### Production (Cloud SQL)
```bash
# Connect to Cloud SQL
gcloud sql connect aibc-postgres --user=postgres --database=aibc_db

# Run migration
\i migrations/001_add_resource_tracking.sql
```

---

## Sample Data Included

The migration script includes sample data for:

### Image Generation Pathway - Module 1
- 5 resources (video, article, exercise, quiz, project)
- File upload enabled for exercise and project
- Accepted file types: images, PDFs (25 MB max)

### Prompt Engineering Pathway - Module 1
- 5 resources (video, article, exercise, quiz, project)
- File upload enabled for exercise and project
- Accepted file types: text, markdown, PDFs, images (10 MB max)

---

## Security Features

### File Upload Security
- **MIME type validation** - Check `file.content_type`
- **Magic bytes validation** - Verify actual file type
- **File size limits** - Configurable per resource
- **Unique filenames** - Add timestamp to prevent overwrites
- **Malware scanning** - (Optional) Integrate Cloud Security Scanner

### Access Control
- **User isolation** - Users can only access their own resources
- **Instructor permissions** - Separate role for reviewing submissions
- **Signed URLs** - Temporary access (1-hour expiry)
- **Rate limiting** - Max 10 uploads/hour per user

### Audit Logging
- All file uploads logged with user_id, resource_id, file metadata
- All reviews logged with reviewer_id, timestamp, action
- Failed uploads logged with error details

---

## Performance Optimizations

### Database
- **Indexes** - All query patterns indexed (see migration script)
- **Triggers** - Automatic progress calculation (no API overhead)
- **Views** - `user_resource_progress_summary`, `pending_submissions`
- **Connection pooling** - Async SQLAlchemy with adaptive pools

### GCS
- **Direct uploads** - No temp storage in FastAPI
- **Signed URLs** - Cached for 1 hour
- **Parallel uploads** - Support concurrent file uploads
- **Resumable uploads** - For large files (future enhancement)

---

## Cost Estimation (60 Users)

### Google Cloud Storage
- **Storage**: 60 users × 50 MB avg = 3 GB
  - Cost: $0.02/GB/month = **$0.06/month**
- **Operations**: 60 users × 20 uploads/month = 1,200 uploads
  - Cost: $0.005/1,000 ops = **$0.01/month**
- **Egress**: Minimal (signed URLs, no direct downloads)
  - Cost: **~$0.00/month**

**Total GCS Cost: ~$0.07/month** (negligible)

### Cloud Run (Backend)
- No change (file uploads are fast, no CPU/memory impact)
- Still **$18-23/month** for 60 users

**Total Cost: ~$18-23/month** (GCS is essentially free)

---

## Next Steps

1. **Run the migration script** on local PostgreSQL
2. **Verify tables created** with sample data
3. **Create SQLAlchemy models** in `app/models/resources.py`
4. **Create Pydantic schemas** in `app/schemas/resources.py`
5. **Implement CRUD operations** in `app/crud/resources.py`
6. **Set up GCS bucket** and service account
7. **Implement GCS integration** in `app/core/gcs.py`
8. **Implement FastAPI endpoints** in `app/api/v1/resources.py`
9. **Test endpoints** with Postman/curl
10. **Integrate with frontend** (pathway page, resource components)

---

## Files Created

1. ✅ **`migrations/001_add_resource_tracking.sql`** - Database migration script
2. ✅ **`docs/API_RESOURCE_TRACKING.md`** - API endpoint documentation
3. ✅ **`docs/RESOURCE_TRACKING_IMPLEMENTATION.md`** - This implementation guide

---

## Questions for Discussion

1. **File retention policy**: How long should we keep uploaded files? (30 days? Forever?)
2. **Review workflow**: Should students be notified when submissions reviewed?
3. **Re-submission policy**: Can students re-upload after "rejected" status?
4. **Grading system**: Simple pass/fail or numeric scores (0-100)?
5. **Quiz implementation**: Store quiz questions in `resources.metadata` JSONB?
6. **Time tracking**: Should frontend track video watch time automatically?
7. **XP/Points system**: Integrate with existing achievements table?

---

**This is a production-ready design that fully supports resource-level progress tracking with file uploads to Google Cloud Storage for the AI Bootcamp platform.**
