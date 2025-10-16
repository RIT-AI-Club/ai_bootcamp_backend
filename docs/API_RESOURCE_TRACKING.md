# Resource-Level Progress Tracking & File Upload API

**Created**: 2025-10-16
**Purpose**: API design for granular resource tracking and GCS file uploads for exercises/projects

---

## Overview

This API extends the existing AI Bootcamp backend to support:
- **Resource-level progress tracking** (videos, articles, exercises, projects, quizzes)
- **File uploads to Google Cloud Storage** for exercise/project submissions
- **Automatic progress calculation** at resource → module → pathway levels
- **Submission review system** for instructors

---

## Database Schema Summary

### New Tables

1. **`resources`** - All pathway resources (videos, articles, exercises, projects)
2. **`resource_completions`** - User progress on each resource
3. **`resource_submissions`** - File uploads to GCS with review status

### Automatic Progress Updates

- **Resource completion** → Triggers module completion check
- **Module completion** → Triggers pathway progress update
- **File upload** → Increments submission count, updates status to "submitted"

---

## API Endpoints

### 1. Resource Management

#### **GET /api/v1/pathways/{pathway_id}/resources**
Get all resources for a pathway (organized by modules)

**Response:**
```json
{
  "pathway_id": "image-generation",
  "modules": [
    {
      "module_id": "foundations-image-gen",
      "title": "Foundations of Image Generation",
      "resources": [
        {
          "id": "foundations-image-gen-r1",
          "type": "video",
          "title": "What is AI Image Generation + Model Types",
          "duration_minutes": 40,
          "requires_upload": false,
          "order_index": 1,
          "url": null
        },
        {
          "id": "foundations-image-gen-r3",
          "type": "exercise",
          "title": "Simple Stable Diffusion prompt generation (Colab)",
          "duration_minutes": 45,
          "requires_upload": true,
          "accepted_file_types": ["image/png", "image/jpeg", "application/pdf"],
          "max_file_size_mb": 25,
          "order_index": 3
        }
      ]
    }
  ]
}
```

#### **GET /api/v1/modules/{module_id}/resources**
Get resources for a specific module

**Response:**
```json
{
  "module_id": "foundations-image-gen",
  "resources": [
    {
      "id": "foundations-image-gen-r1",
      "type": "video",
      "title": "What is AI Image Generation + Model Types",
      "duration_minutes": 40,
      "requires_upload": false,
      "order_index": 1
    }
  ]
}
```

---

### 2. User Progress Tracking

#### **GET /api/v1/users/me/progress/{pathway_id}**
Get comprehensive progress for a pathway (all modules and resources)

**Response:**
```json
{
  "user_id": "uuid",
  "pathway_id": "image-generation",
  "pathway_progress": 35,
  "completed_modules": 1,
  "total_modules": 6,
  "total_time_spent_minutes": 240,
  "started_at": "2025-10-01T10:00:00Z",
  "last_accessed_at": "2025-10-15T14:30:00Z",
  "modules": [
    {
      "module_id": "foundations-image-gen",
      "title": "Foundations of Image Generation",
      "module_progress": 100,
      "completed_at": "2025-10-10T16:20:00Z",
      "resources": [
        {
          "resource_id": "foundations-image-gen-r1",
          "type": "video",
          "title": "What is AI Image Generation + Model Types",
          "status": "completed",
          "progress_percentage": 100,
          "time_spent_minutes": 42,
          "completed_at": "2025-10-05T11:15:00Z"
        },
        {
          "resource_id": "foundations-image-gen-r3",
          "type": "exercise",
          "title": "Simple Stable Diffusion prompt generation (Colab)",
          "status": "submitted",
          "progress_percentage": 100,
          "time_spent_minutes": 50,
          "submission_count": 2,
          "completed_at": "2025-10-08T09:45:00Z",
          "submissions": [
            {
              "id": "uuid",
              "file_name": "stable_diffusion_exercise.png",
              "submission_status": "uploaded",
              "created_at": "2025-10-08T09:45:00Z"
            }
          ]
        }
      ]
    },
    {
      "module_id": "prompt-gemini-nano",
      "title": "Prompt Engineering & Gemini Nano Banana",
      "module_progress": 40,
      "resources": [...]
    }
  ]
}
```

#### **GET /api/v1/users/me/resources/{resource_id}/progress**
Get progress for a specific resource

**Response:**
```json
{
  "user_id": "uuid",
  "resource_id": "foundations-image-gen-r3",
  "resource": {
    "type": "exercise",
    "title": "Simple Stable Diffusion prompt generation (Colab)",
    "requires_upload": true
  },
  "status": "submitted",
  "progress_percentage": 100,
  "time_spent_minutes": 50,
  "started_at": "2025-10-08T08:00:00Z",
  "completed_at": "2025-10-08T09:45:00Z",
  "submission_required": true,
  "submission_count": 2,
  "submissions": [
    {
      "id": "uuid",
      "file_name": "stable_diffusion_v2.png",
      "file_size_bytes": 2048576,
      "file_type": "image/png",
      "gcs_url": "https://storage.googleapis.com/...",
      "submission_status": "uploaded",
      "created_at": "2025-10-08T09:45:00Z"
    }
  ]
}
```

#### **POST /api/v1/users/me/resources/{resource_id}/start**
Mark a resource as started (creates resource_completion record)

**Request Body:**
```json
{
  "notes": "Optional user notes"
}
```

**Response:**
```json
{
  "resource_id": "foundations-image-gen-r1",
  "status": "in_progress",
  "started_at": "2025-10-16T10:00:00Z"
}
```

#### **PUT /api/v1/users/me/resources/{resource_id}/progress**
Update progress on a resource (time spent, percentage, status)

**Request Body:**
```json
{
  "progress_percentage": 100,
  "time_spent_minutes": 42,
  "status": "completed",
  "notes": "Great video, learned about Stable Diffusion vs DALL-E"
}
```

**Response:**
```json
{
  "resource_id": "foundations-image-gen-r1",
  "status": "completed",
  "progress_percentage": 100,
  "time_spent_minutes": 42,
  "completed_at": "2025-10-16T10:42:00Z",
  "module_progress": 20,
  "module_completed": false
}
```

#### **POST /api/v1/users/me/resources/{resource_id}/complete**
Mark a resource as completed (shortcut for 100% progress)

**Response:**
```json
{
  "resource_id": "foundations-image-gen-r1",
  "status": "completed",
  "completed_at": "2025-10-16T10:42:00Z",
  "module_progress": 20,
  "pathway_progress": 3.3
}
```

---

### 3. File Upload & Submission Management

#### **POST /api/v1/users/me/resources/{resource_id}/upload**
Upload a file for an exercise or project to Google Cloud Storage

**Request:**
- `multipart/form-data`
- Field: `file` (binary file data)
- Optional field: `notes` (text)

**Response:**
```json
{
  "submission_id": "uuid",
  "resource_id": "foundations-image-gen-r3",
  "file_name": "stable_diffusion_exercise.png",
  "file_size_bytes": 2048576,
  "file_type": "image/png",
  "gcs_url": "https://storage.googleapis.com/aibc-submissions/pathways/image-generation/users/{user_id}/resources/foundations-image-gen-r3/stable_diffusion_exercise.png",
  "submission_status": "uploaded",
  "created_at": "2025-10-16T11:00:00Z",
  "resource_status": "submitted"
}
```

**Error Responses:**
- `400` - File too large, invalid file type, resource doesn't require upload
- `404` - Resource not found
- `500` - GCS upload failed

#### **GET /api/v1/users/me/resources/{resource_id}/submissions**
Get all submissions for a specific resource

**Response:**
```json
{
  "resource_id": "foundations-image-gen-r3",
  "submissions": [
    {
      "id": "uuid",
      "file_name": "stable_diffusion_v2.png",
      "file_size_bytes": 2048576,
      "file_type": "image/png",
      "gcs_url": "https://storage.googleapis.com/...",
      "submission_status": "uploaded",
      "reviewed_at": null,
      "created_at": "2025-10-08T09:45:00Z"
    },
    {
      "id": "uuid2",
      "file_name": "stable_diffusion_v1.png",
      "submission_status": "uploaded",
      "created_at": "2025-10-08T08:30:00Z"
    }
  ]
}
```

#### **DELETE /api/v1/users/me/submissions/{submission_id}**
Soft delete a submission (sets deleted_at timestamp)

**Response:**
```json
{
  "submission_id": "uuid",
  "deleted": true,
  "deleted_at": "2025-10-16T12:00:00Z"
}
```

#### **GET /api/v1/users/me/submissions/download/{submission_id}**
Get a signed URL to download a specific submission

**Response:**
```json
{
  "submission_id": "uuid",
  "file_name": "stable_diffusion_exercise.png",
  "signed_url": "https://storage.googleapis.com/aibc-submissions/...?X-Goog-Signature=...",
  "expires_at": "2025-10-16T13:00:00Z"
}
```

---

### 4. Instructor Review Endpoints

#### **GET /api/v1/admin/submissions/pending**
Get all pending submissions that need review (instructor only)

**Query Parameters:**
- `pathway_id` (optional) - Filter by pathway
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)

**Response:**
```json
{
  "total_pending": 23,
  "submissions": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_email": "student@example.com",
      "user_name": "John Doe",
      "resource_id": "foundations-image-gen-r5",
      "resource_title": "Generate 3 mood-board images for fictional product",
      "resource_type": "project",
      "pathway_id": "image-generation",
      "file_name": "mood_board.pdf",
      "gcs_url": "https://storage.googleapis.com/...",
      "submission_status": "uploaded",
      "created_at": "2025-10-15T14:20:00Z",
      "hours_waiting": 22.5
    }
  ]
}
```

#### **POST /api/v1/admin/submissions/{submission_id}/review**
Review and grade a submission (instructor only)

**Request Body:**
```json
{
  "submission_status": "approved",
  "review_comments": "Great work! The mood board clearly shows the design direction.",
  "grade": "pass"
}
```

**Response:**
```json
{
  "submission_id": "uuid",
  "submission_status": "approved",
  "reviewed_by": "instructor_uuid",
  "reviewed_at": "2025-10-16T12:30:00Z",
  "review_comments": "Great work!",
  "grade": "pass"
}
```

---

## Google Cloud Storage Configuration

### Bucket Structure

```
aibc-submissions/
├── pathways/
│   ├── image-generation/
│   │   ├── users/
│   │   │   ├── {user_id}/
│   │   │   │   ├── resources/
│   │   │   │   │   ├── {resource_id}/
│   │   │   │   │   │   ├── {timestamp}_{filename}
│   ├── prompt-engineering/
│   │   ├── users/
│   │   │   ├── {user_id}/...
```

### GCS Permissions

- **Service Account**: `aibc-backend@project.iam.gserviceaccount.com`
- **Roles**:
  - `Storage Object Creator` (write files)
  - `Storage Object Viewer` (read files for signed URLs)

### File Upload Flow

1. **Frontend** → Sends file to FastAPI endpoint
2. **FastAPI** → Validates file (size, type, user permissions)
3. **FastAPI** → Uploads to GCS with structured path
4. **FastAPI** → Creates `resource_submissions` record
5. **Database Trigger** → Updates `resource_completions.submission_count`
6. **Database Trigger** → Updates resource status to "submitted"
7. **FastAPI** → Returns GCS URL and metadata

---

## Implementation Phases

### **Phase 1: Database Setup** ✅ DONE
- [x] Create migration script (`001_add_resource_tracking.sql`)
- [x] Add tables: `resources`, `resource_completions`, `resource_submissions`
- [x] Add triggers for automatic progress calculation
- [x] Add helper functions
- [x] Insert sample data for image-generation and prompt-engineering

### **Phase 2: Backend Models & CRUD** (Next)
- [ ] Create SQLAlchemy models for new tables
- [ ] Create Pydantic schemas for requests/responses
- [ ] Build CRUD operations in `app/crud/resources.py`
- [ ] Build CRUD operations in `app/crud/submissions.py`

### **Phase 3: FastAPI Endpoints** (Next)
- [ ] Implement resource management endpoints
- [ ] Implement progress tracking endpoints
- [ ] Implement file upload with GCS integration
- [ ] Implement submission review endpoints
- [ ] Add authentication & authorization

### **Phase 4: GCS Integration**
- [ ] Set up GCS bucket and service account
- [ ] Implement upload helper functions
- [ ] Implement signed URL generation
- [ ] Add file validation (size, type, malware scan)

### **Phase 5: Frontend Integration**
- [ ] Update pathway page to show resources
- [ ] Add resource checkboxes for videos/articles
- [ ] Add file upload UI for exercises/projects
- [ ] Add progress bars at resource/module/pathway levels
- [ ] Add submission history view

### **Phase 6: Testing & Deployment**
- [ ] Unit tests for CRUD operations
- [ ] Integration tests for file uploads
- [ ] End-to-end tests for progress tracking
- [ ] Load testing for GCS uploads
- [ ] Deploy to Cloud Run

---

## Configuration & Policy

### File Management Policies
- **Retention**: Files stored **permanently** in GCS (no automatic deletion)
- **Max File Size**: **50 MB** per file (configurable per resource type)
- **Resubmission**: ✅ **Allowed** - Students can re-upload after rejection
- **Storage**: Google Cloud Storage with structured paths

### Grading System
- **Format**: Simple **pass/fail** binary grading
- **Reviews**: Instructors provide grade + optional text comments
- **Notifications**: Email notifications **not implemented** (future enhancement)

### Quiz System
- **Storage**: Questions/answers stored in `resources.metadata` JSONB field
- **Format**: Matches `Quiz.tsx` component structure (see frontend)
- **Scoring**: Client-side calculation, results stored in `resource_completions.metadata`
- **Passing Score**: Configurable per quiz (default 70%)

---

## Security Considerations

1. **File Upload Security**
   - Validate file types via MIME type AND magic bytes
   - Scan uploads for malware (Cloud Security Scanner)
   - Limit file sizes (50 MB max, configurable per resource)
   - Generate unique filenames with timestamps to prevent overwriting

2. **Access Control**
   - Users can only upload to their own resources
   - Users can only view their own submissions
   - Instructors can view all submissions for review
   - Use signed URLs for temporary file access (1-hour expiry)

3. **Rate Limiting**
   - Max 10 uploads per user per hour
   - Max 100 MB total uploads per user per day

4. **Data Privacy**
   - Soft delete submissions (never hard delete, set `deleted_at`)
   - Files kept forever unless explicitly deleted by admin
   - Anonymize user data on account deletion
   - Audit log all file access

---

## Example User Flows

### **Flow 1: Complete a Video Resource**
1. User clicks on video → `POST /api/v1/users/me/resources/{resource_id}/start`
2. User watches video (frontend tracks time)
3. User completes video → `POST /api/v1/users/me/resources/{resource_id}/complete`
4. Backend updates `resource_completions.status = 'completed'`
5. Trigger checks if all module resources complete → auto-complete module

### **Flow 2: Submit an Exercise with File Upload**
1. User starts exercise → `POST /api/v1/users/me/resources/{resource_id}/start`
2. User completes exercise locally
3. User uploads file → `POST /api/v1/users/me/resources/{resource_id}/upload`
4. Backend uploads to GCS → Creates `resource_submissions` record
5. Trigger updates `resource_completions.status = 'submitted'`
6. Trigger checks module completion → auto-complete if all done

### **Flow 3: Instructor Reviews Submission**
1. Instructor views pending → `GET /api/v1/admin/submissions/pending`
2. Instructor downloads file → `GET /api/v1/users/me/submissions/download/{submission_id}`
3. Instructor reviews and grades → `POST /api/v1/admin/submissions/{submission_id}/review`
4. Backend updates `resource_submissions.submission_status = 'approved'`
5. User sees approval status in their progress view

---

## Performance Optimizations

1. **Database Indexes** - All query patterns indexed (see migration script)
2. **Materialized Views** - User progress summaries pre-calculated
3. **Async Operations** - All database queries use async SQLAlchemy
4. **Connection Pooling** - Adaptive pooling for Cloud Run (2+3) vs local (5+10)
5. **Caching** - No Redis needed (PostgreSQL sufficient for 60 users)
6. **GCS Optimization** - Direct uploads (no temp storage), signed URLs cached 1 hour

---

## Monitoring & Metrics

### Key Metrics to Track
- **Progress Metrics**: Completion rates by pathway, module, resource type
- **Upload Metrics**: Files uploaded/day, file sizes, upload success rate
- **Review Metrics**: Time to review, approval rate, pending queue size
- **Performance**: API response times, GCS upload latency, database query performance

### Logging
- All file uploads logged with user_id, resource_id, file metadata
- All submission reviews logged with reviewer_id, timestamp, action
- Failed uploads logged with error details

---

This API design provides **complete resource-level tracking** with **file upload support** and **automatic progress calculation** for the AI Bootcamp platform.
