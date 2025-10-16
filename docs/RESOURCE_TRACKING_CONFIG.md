# Resource Tracking Configuration Reference

**Last Updated:** 2025-10-16
**Status:** Configuration Complete

---

## Quick Configuration Summary

| Setting | Value | Location |
|---------|-------|----------|
| **File Retention** | Forever (permanent storage) | GCS Bucket |
| **Max File Size** | 50 MB (global max) | `resources.max_file_size_mb` |
| **Resubmission** | Allowed after rejection | `resources.allow_resubmission = TRUE` |
| **Grading** | Pass/Fail only | `resource_submissions.grade` |
| **Email Notifications** | Not implemented | N/A |
| **Quiz Storage** | JSONB metadata | `resources.metadata` |

---

## File Upload Configuration

### Global Settings
```sql
-- Default max file size (can be overridden per resource)
max_file_size_mb: 50 MB

-- Resubmission policy
allow_resubmission: TRUE (students can re-upload after rejection)

-- Retention policy
retention: PERMANENT (files never auto-deleted)
```

### Per-Resource Configuration
Resources can override file upload settings:

```sql
-- Image-heavy resources (image-generation pathway)
max_file_size_mb: 25 MB
accepted_file_types: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf']

-- Text/document resources (prompt-engineering pathway)
max_file_size_mb: 10 MB
accepted_file_types: ['text/plain', 'text/markdown', 'application/pdf', 'image/png', 'image/jpeg']
```

### Accepted File Types by Resource Type

| Resource Type | Common File Types | Max Size |
|--------------|-------------------|----------|
| **Exercise (Image Gen)** | PNG, JPEG, JPG, WEBP, PDF | 25 MB |
| **Project (Image Gen)** | PNG, JPEG, JPG, WEBP, PDF | 25 MB |
| **Exercise (Prompt Eng)** | TXT, MD, PDF, PNG, JPEG | 10 MB |
| **Project (Prompt Eng)** | TXT, MD, PDF, PNG, JPEG | 10 MB |
| **General Exercise** | All above | 50 MB |
| **General Project** | All above | 50 MB |

---

## Grading & Review System

### Grading Options
```sql
grade: 'pass' | 'fail' | NULL
```

Simple binary grading system:
- **Pass**: Student submission meets requirements
- **Fail**: Student submission needs improvement (can resubmit)
- **NULL**: Not yet reviewed

### Review Workflow
1. Student uploads file → `submission_status = 'uploaded'`
2. Instructor views submission → Downloads via signed URL
3. Instructor reviews → Sets grade + optional comments
4. If **pass**: `submission_status = 'approved'`, resource marked complete
5. If **fail**: `submission_status = 'rejected'`, student can resubmit

### Review Fields
```sql
reviewed_by: UUID (instructor user_id)
reviewed_at: TIMESTAMP
review_comments: TEXT (optional feedback)
grade: 'pass' | 'fail'
```

---

## Quiz System

### Storage Format
Quizzes stored in `resources.metadata` JSONB field, matching `Quiz.tsx` component:

```json
{
  "title": "Quiz Title",
  "description": "Optional description",
  "passingScore": 70,
  "questions": [
    {
      "id": "q1",
      "type": "multiple-choice",
      "question": "Question text?",
      "options": [
        {"id": "a", "text": "Option A", "isCorrect": false},
        {"id": "b", "text": "Option B", "isCorrect": true},
        {"id": "c", "text": "Option C", "isCorrect": false},
        {"id": "d", "text": "Option D", "isCorrect": false}
      ],
      "explanation": "Why B is correct..."
    },
    {
      "id": "q2",
      "type": "true-false",
      "question": "Statement to evaluate?",
      "options": [
        {"id": "true", "text": "True", "isCorrect": true},
        {"id": "false", "text": "False", "isCorrect": false}
      ],
      "explanation": "Why true is correct..."
    }
  ]
}
```

### Quiz Question Types
- **`multiple-choice`**: 2-6 options, one correct answer
- **`true-false`**: Boolean questions with explanation

### Quiz Scoring
- **Calculated**: Client-side by `Quiz.tsx` component
- **Passing Score**: Configurable per quiz (default 70%)
- **Results Stored**: In `resource_completions.metadata`:
  ```json
  {
    "quiz_score": 85,
    "quiz_passed": true,
    "quiz_attempts": 1,
    "quiz_completed_at": "2025-10-16T14:30:00Z",
    "selected_answers": {
      "q1": "b",
      "q2": "true"
    }
  }
  ```

---

## Progress Tracking

### Status Values
```sql
-- resource_completions.status
'not_started'  -- Resource not yet accessed
'in_progress'  -- Resource started but not completed
'completed'    -- Resource fully completed (videos, articles, quizzes)
'submitted'    -- Exercise/project file uploaded, awaiting review
'reviewed'     -- Submission reviewed and approved
```

### Automatic Progress Updates
All handled by database triggers:

1. **Resource Complete** → Check if all module resources complete → Auto-complete module
2. **Module Complete** → Check if all pathway modules complete → Auto-complete pathway
3. **File Upload** → Increment submission count → Set status to 'submitted'

---

## Google Cloud Storage Setup

### Bucket Configuration
```bash
Bucket Name: aibc-submissions
Region: us-central1
Storage Class: Standard
Access Control: Uniform (IAM only)
Lifecycle: None (files kept forever)
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
│   │   │   │   │   │   ├── 2025-10-17_09-15-00_filename_v2.png
│   ├── prompt-engineering/
│   │   ├── users/...
```

### File Naming Convention
```
{timestamp}_{original_filename}
Example: 2025-10-16_14-30-00_my_exercise.png
```

Ensures:
- No overwrites (unique timestamp)
- Chronological ordering
- Original filename preserved

---

## Database Table Summary

### `resources` Table
Stores all pathway resources (videos, articles, exercises, projects, quizzes)

**Key Fields:**
- `type`: 'video', 'article', 'exercise', 'project', 'quiz'
- `requires_upload`: Boolean (TRUE for exercises/projects)
- `max_file_size_mb`: Per-resource file size limit
- `allow_resubmission`: Allow re-upload after rejection
- `metadata`: JSONB (quiz questions, exercise instructions)

### `resource_completions` Table
Tracks user progress on each resource

**Key Fields:**
- `status`: 'not_started', 'in_progress', 'completed', 'submitted', 'reviewed'
- `progress_percentage`: 0-100%
- `submission_count`: Number of files uploaded
- `metadata`: JSONB (quiz results, notes)

### `resource_submissions` Table
Tracks file uploads to GCS

**Key Fields:**
- `gcs_bucket`, `gcs_path`, `gcs_url`: GCS location
- `submission_status`: 'uploading', 'uploaded', 'approved', 'rejected', 'failed'
- `grade`: 'pass' | 'fail' | NULL
- `reviewed_by`, `reviewed_at`, `review_comments`: Review metadata
- `deleted_at`: Soft delete timestamp

---

## Rate Limiting & Quotas

### Upload Limits (Per User)
```
Max uploads per hour: 10 files
Max total upload per day: 100 MB
Max file size: 50 MB (configurable per resource)
```

### API Rate Limits
```
Progress updates: 100/minute
File uploads: 10/hour
Quiz submissions: 50/hour
```

---

## Email Notifications

**Status:** ❌ Not Implemented

Email notifications are **not currently implemented**. This includes:
- No emails when submissions reviewed
- No emails when grades posted
- No emails on pathway/module completion

**Future Enhancement:** Can be added later using:
- SendGrid API
- AWS SES
- Google Cloud Email API

---

## Environment Variables

### Required for GCS Integration
```bash
# Add to aibc_auth/.env
GCS_BUCKET_NAME=aibc-submissions
GCS_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

### Required for Resource Tracking
```bash
# Already in .env (no new vars needed)
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
```

---

## Migration Execution

### Local Development
```bash
# Run the migration
docker exec -i aibc_postgres psql -U postgres -d aibc_db < migrations/001_add_resource_tracking.sql

# Verify tables created
docker exec -it aibc_postgres psql -U postgres -d aibc_db -c "\dt resources*"
```

### Production (Cloud SQL)
```bash
# Connect to Cloud SQL
gcloud sql connect aibc-postgres --user=postgres --database=aibc_db

# Run migration
\i migrations/001_add_resource_tracking.sql

# Verify
\dt resources*
SELECT * FROM resources LIMIT 5;
```

---

## Sample Data Included

Migration includes sample data for:

### Image Generation Pathway - Module 1
- ✅ 5 resources (video, article, exercise, quiz, project)
- ✅ Quiz with 2 sample questions in metadata
- ✅ File upload enabled for exercise and project

### Prompt Engineering Pathway - Module 1
- ✅ 5 resources (video, article, exercise, quiz, project)
- ✅ Quiz with 2 sample questions in metadata
- ✅ File upload enabled for exercise and project

---

## Cost Estimation

### GCS Storage (60 Users)
```
Storage: 60 users × 50 MB avg = 3 GB
Cost: $0.02/GB/month = $0.06/month

Operations: 60 users × 20 uploads/month = 1,200 ops
Cost: $0.005/1,000 ops = $0.01/month

Total GCS: ~$0.07/month (negligible)
```

### Cloud Run (No Change)
```
Backend service: $18-23/month (same as before)
Total system: ~$18-23/month for 60 users
```

---

## API Endpoints Summary

### Progress Tracking
- `GET /api/v1/pathways/{pathway_id}/resources` - Get all resources
- `GET /api/v1/users/me/progress/{pathway_id}` - Full progress report
- `POST /api/v1/users/me/resources/{resource_id}/complete` - Mark complete

### File Uploads
- `POST /api/v1/users/me/resources/{resource_id}/upload` - Upload file
- `GET /api/v1/users/me/resources/{resource_id}/submissions` - List submissions
- `GET /api/v1/users/me/submissions/download/{id}` - Get signed URL

### Instructor Review
- `GET /api/v1/admin/submissions/pending` - Pending reviews
- `POST /api/v1/admin/submissions/{id}/review` - Grade submission

---

## Security Features

### File Upload Security
✅ MIME type validation
✅ Magic bytes verification
✅ File size limits (50 MB max)
✅ Unique filenames with timestamps
✅ Rate limiting (10 uploads/hour)

### Access Control
✅ Users can only access their own resources
✅ Instructors can view all submissions
✅ Signed URLs (1-hour expiry)
✅ Soft deletes only (no hard deletes)

### Audit Logging
✅ All uploads logged with user_id, resource_id, timestamp
✅ All reviews logged with reviewer_id, grade, timestamp
✅ Failed uploads logged with error details

---

## Next Implementation Steps

1. **Run migration script** on local PostgreSQL ✅
2. **Create SQLAlchemy models** for new tables
3. **Create Pydantic schemas** for API requests/responses
4. **Implement CRUD operations** in `app/crud/resources.py`
5. **Set up GCS bucket** and service account
6. **Implement GCS upload** in `app/core/gcs.py`
7. **Create FastAPI endpoints** in `app/api/v1/resources.py`
8. **Test with Postman/curl**
9. **Integrate with frontend** (pathway page, upload UI)

---

**This configuration ensures a simple, scalable, and cost-effective resource tracking system with file uploads for the AI Bootcamp platform.**
