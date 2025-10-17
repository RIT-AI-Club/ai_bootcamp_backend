from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ============================================================================
# Resource Schemas
# ============================================================================

class ResourceBase(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    order_index: int
    duration_minutes: Optional[int] = None
    requires_upload: bool = False
    accepted_file_types: Optional[List[str]] = None
    max_file_size_mb: int = 50
    allow_resubmission: bool = True
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias='resource_metadata')

class ResourceResponse(ResourceBase):
    id: str
    module_id: str
    pathway_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# ============================================================================
# Resource Completion Schemas
# ============================================================================

class ResourceCompletionCreate(BaseModel):
    resource_id: Optional[str] = None  # Optional since endpoint uses path parameter
    notes: Optional[str] = None

class ResourceCompletionUpdate(BaseModel):
    status: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    time_spent_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['not_started', 'in_progress', 'completed', 'submitted', 'reviewed']:
            raise ValueError('Invalid status')
        return v

class ResourceCompletionResponse(BaseModel):
    id: UUID
    user_id: UUID
    resource_id: str
    module_id: str
    pathway_id: str
    status: str
    progress_percentage: int
    time_spent_minutes: int
    started_at: datetime
    completed_at: Optional[datetime]
    last_accessed_at: datetime
    submission_required: bool
    submission_count: int
    notes: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(None, alias='completion_metadata')

    class Config:
        from_attributes = True
        populate_by_name = True

# ============================================================================
# Resource Submission Schemas
# ============================================================================

class ResourceSubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    resource_id: str
    file_name: str
    file_size_bytes: int
    file_type: str
    gcs_url: str
    submission_status: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_comments: Optional[str]
    grade: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = Field(None, alias='submission_metadata')

    class Config:
        from_attributes = True
        populate_by_name = True

class SubmissionReviewRequest(BaseModel):
    submission_status: str = Field(..., pattern='^(approved|rejected)$')
    review_comments: Optional[str] = None
    grade: str = Field(..., pattern='^(pass|fail)$')

    @validator('submission_status')
    def validate_submission_status(cls, v):
        if v not in ['approved', 'rejected']:
            raise ValueError('submission_status must be either approved or rejected')
        return v

    @validator('grade')
    def validate_grade(cls, v):
        if v not in ['pass', 'fail']:
            raise ValueError('grade must be either pass or fail')
        return v

# ============================================================================
# Combined Progress Response Schemas
# ============================================================================

class ResourceWithProgress(ResourceResponse):
    completion: Optional[ResourceCompletionResponse] = None
    submissions: Optional[List[ResourceSubmissionResponse]] = None

class ModuleResourcesResponse(BaseModel):
    module_id: str
    module_title: str
    resources: List[ResourceWithProgress]

class PathwayProgressResponse(BaseModel):
    user_id: UUID
    pathway_id: str
    pathway_title: str
    pathway_progress: int
    completed_modules: int
    total_modules: int
    total_time_spent_minutes: int
    started_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    completed_at: Optional[datetime]
    modules: List[ModuleResourcesResponse]

# ============================================================================
# Pending Submission Response (for instructors)
# ============================================================================

class PendingSubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    resource_id: str
    resource_title: str
    resource_type: str
    pathway_id: str
    module_id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    gcs_url: str
    submission_status: str
    created_at: datetime
    hours_waiting: float

    class Config:
        from_attributes = True

class PendingSubmissionsListResponse(BaseModel):
    total_pending: int
    submissions: List[PendingSubmissionResponse]

# ============================================================================
# File Upload Response
# ============================================================================

class FileUploadResponse(BaseModel):
    submission_id: UUID
    resource_id: str
    file_name: str
    file_size_bytes: int
    file_type: str
    gcs_url: str
    submission_status: str
    created_at: datetime
    resource_status: str
    message: str = "File uploaded successfully"

# ============================================================================
# Signed URL Response
# ============================================================================

class SignedURLResponse(BaseModel):
    submission_id: UUID
    file_name: str
    signed_url: str
    expires_at: datetime
