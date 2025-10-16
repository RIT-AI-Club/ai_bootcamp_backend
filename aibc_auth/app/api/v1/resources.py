from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID
from app.db.database import get_db
from app.schemas.resource import (
    ResourceResponse, ResourceCompletionCreate, ResourceCompletionUpdate,
    ResourceCompletionResponse, ModuleResourcesResponse, PathwayProgressResponse,
    ResourceWithProgress, FileUploadResponse, SignedURLResponse,
    ResourceSubmissionResponse, PendingSubmissionsListResponse, SubmissionReviewRequest,
    PendingSubmissionResponse
)
from app.crud import resource as resource_crud
from app.core.security import get_current_user, limiter
from app.core.gcs import (
    get_gcs_manager, validate_file_upload, generate_unique_filename, build_gcs_path
)
from app.core.config import settings
from app.models.user import User
from app.models.progress import Module
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# Resource Management Endpoints
# ============================================================================

@router.get("/pathways/{pathway_id}/resources", response_model=List[ModuleResourcesResponse])
async def get_pathway_resources(
    pathway_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resources for a pathway, grouped by modules"""
    try:
        # Get all modules for the pathway
        from sqlalchemy import select
        result = await db.execute(
            select(Module)
            .where(Module.pathway_id == pathway_id)
            .order_by(Module.order_index)
        )
        modules = result.scalars().all()

        # Build response with resources for each module
        response = []
        for module in modules:
            resources = await resource_crud.get_resources_by_module(db, module.id)

            # Get user's completion status for each resource
            resources_with_progress = []
            for resource in resources:
                completion = await resource_crud.get_resource_completion(
                    db, current_user.id, resource.id
                )

                # Get submissions if completion exists and resource requires upload
                submissions = []
                if completion and resource.requires_upload:
                    submissions = await resource_crud.get_submissions_for_resource(
                        db, current_user.id, resource.id
                    )

                resource_dict = ResourceResponse.model_validate(resource)
                resources_with_progress.append(ResourceWithProgress(
                    **resource_dict.model_dump(),
                    completion=ResourceCompletionResponse.model_validate(completion) if completion else None,
                    submissions=[ResourceSubmissionResponse.model_validate(s) for s in submissions]
                ))

            response.append(ModuleResourcesResponse(
                module_id=module.id,
                module_title=module.title,
                resources=resources_with_progress
            ))

        return response

    except Exception as e:
        logger.error(f"Error fetching pathway resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pathway resources"
        )

@router.get("/modules/{module_id}/resources", response_model=List[ResourceResponse])
async def get_module_resources(
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resources for a specific module"""
    try:
        resources = await resource_crud.get_resources_by_module(db, module_id)
        return [ResourceResponse.model_validate(r) for r in resources]
    except Exception as e:
        logger.error(f"Error fetching module resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch module resources"
        )

@router.get("/modules/{module_id}/resources-with-progress", response_model=List[ResourceWithProgress])
async def get_module_resources_with_progress(
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resources for a module WITH user progress and submissions (optimized single query)"""
    try:
        # Get all resources for the module
        resources = await resource_crud.get_resources_by_module(db, module_id)

        if not resources:
            return []

        # Build response with progress for each resource
        resources_with_progress = []
        for resource in resources:
            # Get user's completion status
            completion = await resource_crud.get_resource_completion(
                db, current_user.id, resource.id
            )

            # Get submissions if resource requires upload
            submissions = []
            if resource.requires_upload:
                submissions = await resource_crud.get_submissions_for_resource(
                    db, current_user.id, resource.id
                )

            resource_dict = ResourceResponse.model_validate(resource)
            resources_with_progress.append(ResourceWithProgress(
                **resource_dict.model_dump(),
                completion=ResourceCompletionResponse.model_validate(completion) if completion else None,
                submissions=[ResourceSubmissionResponse.model_validate(s) for s in submissions]
            ))

        return resources_with_progress

    except Exception as e:
        logger.error(f"Error fetching module resources with progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch module resources with progress"
        )

# ============================================================================
# Progress Tracking Endpoints
# ============================================================================

@router.get("/users/me/resources/{resource_id}/progress", response_model=ResourceCompletionResponse)
async def get_resource_progress(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's progress on a specific resource"""
    completion = await resource_crud.get_resource_completion(db, current_user.id, resource_id)

    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource completion not found"
        )

    return ResourceCompletionResponse.model_validate(completion)

@router.post("/users/me/resources/{resource_id}/start", response_model=ResourceCompletionResponse)
@limiter.limit("100/minute")
async def start_resource(
    request: Request,
    resource_id: str,
    data: Optional[ResourceCompletionCreate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a resource as started"""
    try:
        # Check if already started
        existing = await resource_crud.get_resource_completion(db, current_user.id, resource_id)
        if existing:
            return ResourceCompletionResponse.model_validate(existing)

        # Create new completion record
        completion = await resource_crud.create_resource_completion(
            db,
            current_user.id,
            resource_id,
            notes=data.notes if data else None
        )

        logger.info(f"User {current_user.email} started resource {resource_id}")
        return ResourceCompletionResponse.model_validate(completion)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start resource"
        )

@router.put("/users/me/resources/{resource_id}/progress", response_model=ResourceCompletionResponse)
@limiter.limit("100/minute")
async def update_resource_progress(
    request: Request,
    resource_id: str,
    data: ResourceCompletionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update progress on a resource"""
    try:
        # Get existing completion
        completion = await resource_crud.get_resource_completion(db, current_user.id, resource_id)

        if not completion:
            # Auto-create if doesn't exist
            completion = await resource_crud.create_resource_completion(
                db, current_user.id, resource_id
            )

        # Update completion
        updated = await resource_crud.update_resource_completion(
            db,
            completion.id,
            status=data.status,
            progress_percentage=data.progress_percentage,
            time_spent_minutes=data.time_spent_minutes,
            notes=data.notes,
            metadata=data.metadata
        )

        return ResourceCompletionResponse.model_validate(updated)

    except Exception as e:
        logger.error(f"Error updating resource progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resource progress"
        )

@router.post("/users/me/resources/{resource_id}/complete", response_model=ResourceCompletionResponse)
@limiter.limit("100/minute")
async def complete_resource(
    request: Request,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a resource as completed"""
    try:
        # Get or create completion
        completion = await resource_crud.get_resource_completion(db, current_user.id, resource_id)

        if not completion:
            completion = await resource_crud.create_resource_completion(
                db, current_user.id, resource_id
            )

        # Update to completed status
        updated = await resource_crud.update_resource_completion(
            db,
            completion.id,
            status='completed',
            progress_percentage=100
        )

        logger.info(f"User {current_user.email} completed resource {resource_id}")
        return ResourceCompletionResponse.model_validate(updated)

    except Exception as e:
        logger.error(f"Error completing resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete resource"
        )

# ============================================================================
# File Upload Endpoints
# ============================================================================

@router.post("/users/me/resources/{resource_id}/upload", response_model=FileUploadResponse)
@limiter.limit("10/hour")
async def upload_resource_file(
    request: Request,
    resource_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a file for an exercise or project"""
    try:
        # Get resource
        resource = await resource_crud.get_resource_by_id(db, resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )

        # Check if resource requires upload
        if not resource.requires_upload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This resource does not accept file uploads"
            )

        # Get or create completion record
        completion = await resource_crud.get_resource_completion(db, current_user.id, resource_id)
        if not completion:
            completion = await resource_crud.create_resource_completion(
                db, current_user.id, resource_id
            )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file
        is_valid, error_msg = validate_file_upload(
            file.filename,
            file_size,
            resource.accepted_file_types,
            resource.max_file_size_mb
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Generate unique filename and GCS path
        unique_filename = generate_unique_filename(file.filename)
        gcs_path = build_gcs_path(
            resource.pathway_id,
            str(current_user.id),
            resource_id,
            unique_filename
        )

        # Upload to GCS
        gcs_manager = get_gcs_manager()
        from io import BytesIO
        gcs_url = gcs_manager.upload_file(
            BytesIO(file_content),
            gcs_path,
            file.content_type
        )

        # Create submission record
        submission = await resource_crud.create_resource_submission(
            db,
            user_id=current_user.id,
            resource_id=resource_id,
            resource_completion_id=completion.id,
            file_name=file.filename,
            file_size_bytes=file_size,
            file_type=file.content_type,
            gcs_bucket=settings.GCS_BUCKET_NAME,
            gcs_path=gcs_path,
            gcs_url=gcs_url,
            upload_ip=request.client.host if request.client else None
        )

        # Refresh completion to get updated status (trigger sets status to 'submitted')
        await db.refresh(completion)

        logger.info(f"User {current_user.email} uploaded file for resource {resource_id}")

        return FileUploadResponse(
            submission_id=submission.id,
            resource_id=resource_id,
            file_name=file.filename,
            file_size_bytes=file_size,
            file_type=file.content_type,
            gcs_url=gcs_url,
            submission_status=submission.submission_status,
            created_at=submission.created_at,
            resource_status=completion.status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )

@router.get("/users/me/resources/{resource_id}/submissions", response_model=List[ResourceSubmissionResponse])
async def get_resource_submissions(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all submissions for a user's resource"""
    try:
        submissions = await resource_crud.get_submissions_for_resource(
            db, current_user.id, resource_id
        )
        return [ResourceSubmissionResponse.model_validate(s) for s in submissions]
    except Exception as e:
        logger.error(f"Error fetching submissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch submissions"
        )

@router.get("/users/me/submissions/download/{submission_id}", response_model=SignedURLResponse)
async def get_submission_download_url(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a signed URL to download a submission"""
    try:
        submission = await resource_crud.get_submission_by_id(db, submission_id)

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )

        # Check ownership
        if submission.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this submission"
            )

        # Generate signed URL
        gcs_manager = get_gcs_manager()
        signed_url = gcs_manager.generate_signed_url(submission.gcs_path, expiration_hours=1)

        return SignedURLResponse(
            submission_id=submission.id,
            file_name=submission.file_name,
            signed_url=signed_url,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

@router.delete("/users/me/submissions/{submission_id}")
async def delete_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a submission"""
    try:
        submission = await resource_crud.get_submission_by_id(db, submission_id)

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )

        # Check ownership
        if submission.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this submission"
            )

        await resource_crud.soft_delete_submission(db, submission_id)

        logger.info(f"User {current_user.email} deleted submission {submission_id}")

        return {"message": "Submission deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete submission"
        )

# ============================================================================
# Instructor Review Endpoints
# ============================================================================

@router.get("/admin/submissions/pending", response_model=PendingSubmissionsListResponse)
async def get_pending_submissions(
    pathway_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending submissions for instructor review (admin only)"""
    # TODO: Add admin role check here when roles are implemented
    try:
        total_count, submissions = await resource_crud.get_pending_submissions(
            db, pathway_id, limit, offset
        )

        return PendingSubmissionsListResponse(
            total_pending=total_count,
            submissions=[PendingSubmissionResponse(**s) for s in submissions]
        )

    except Exception as e:
        logger.error(f"Error fetching pending submissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pending submissions"
        )

@router.post("/admin/submissions/{submission_id}/review", response_model=ResourceSubmissionResponse)
async def review_submission(
    submission_id: UUID,
    review: SubmissionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Review and grade a submission (admin only)"""
    # TODO: Add admin role check here when roles are implemented
    try:
        submission = await resource_crud.get_submission_by_id(db, submission_id)

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )

        # Update submission with review
        updated = await resource_crud.update_submission_review(
            db,
            submission_id,
            current_user.id,
            review.submission_status,
            review.grade,
            review.review_comments
        )

        logger.info(f"Instructor {current_user.email} reviewed submission {submission_id}: {review.grade}")

        return ResourceSubmissionResponse.model_validate(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review submission"
        )
