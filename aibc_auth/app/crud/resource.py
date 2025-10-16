from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, text
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
from app.models.resource import Resource, ResourceCompletion, ResourceSubmission
from app.models.progress import Module
from app.models.user import User

# ============================================================================
# Resource CRUD Operations
# ============================================================================

async def get_resource_by_id(db: AsyncSession, resource_id: str) -> Optional[Resource]:
    """Get a single resource by ID"""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    return result.scalar_one_or_none()

async def get_resources_by_module(db: AsyncSession, module_id: str) -> List[Resource]:
    """Get all resources for a specific module, ordered by order_index"""
    result = await db.execute(
        select(Resource)
        .where(Resource.module_id == module_id)
        .order_by(Resource.order_index)
    )
    return result.scalars().all()

async def get_resources_by_pathway(db: AsyncSession, pathway_id: str) -> List[Resource]:
    """Get all resources for a pathway"""
    result = await db.execute(
        select(Resource)
        .where(Resource.pathway_id == pathway_id)
        .order_by(Resource.module_id, Resource.order_index)
    )
    return result.scalars().all()

# ============================================================================
# Resource Completion CRUD Operations
# ============================================================================

async def get_resource_completion(
    db: AsyncSession,
    user_id: UUID,
    resource_id: str
) -> Optional[ResourceCompletion]:
    """Get a user's completion record for a specific resource"""
    result = await db.execute(
        select(ResourceCompletion).where(
            and_(
                ResourceCompletion.user_id == user_id,
                ResourceCompletion.resource_id == resource_id
            )
        )
    )
    return result.scalar_one_or_none()

async def create_resource_completion(
    db: AsyncSession,
    user_id: UUID,
    resource_id: str,
    notes: Optional[str] = None
) -> ResourceCompletion:
    """Create a new resource completion record"""
    # Get resource to populate module_id and pathway_id
    resource = await get_resource_by_id(db, resource_id)
    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    completion = ResourceCompletion(
        user_id=user_id,
        resource_id=resource_id,
        module_id=resource.module_id,
        pathway_id=resource.pathway_id,
        status='in_progress',
        submission_required=resource.requires_upload,
        notes=notes
    )
    db.add(completion)
    await db.commit()
    await db.refresh(completion)
    return completion

async def update_resource_completion(
    db: AsyncSession,
    completion_id: UUID,
    status: Optional[str] = None,
    progress_percentage: Optional[int] = None,
    time_spent_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    metadata: Optional[dict] = None
) -> ResourceCompletion:
    """Update an existing resource completion record"""
    values = {
        "last_accessed_at": datetime.now(timezone.utc)
    }

    if status is not None:
        values["status"] = status
        if status in ['completed', 'submitted', 'reviewed']:
            values["completed_at"] = datetime.now(timezone.utc)
            values["progress_percentage"] = 100

    if progress_percentage is not None:
        values["progress_percentage"] = progress_percentage

    if time_spent_minutes is not None:
        values["time_spent_minutes"] = time_spent_minutes

    if notes is not None:
        values["notes"] = notes

    if metadata is not None:
        values["completion_metadata"] = metadata

    await db.execute(
        update(ResourceCompletion)
        .where(ResourceCompletion.id == completion_id)
        .values(**values)
    )
    await db.commit()

    # Return updated completion
    result = await db.execute(
        select(ResourceCompletion).where(ResourceCompletion.id == completion_id)
    )
    return result.scalar_one()

async def get_user_completions_for_module(
    db: AsyncSession,
    user_id: UUID,
    module_id: str
) -> List[ResourceCompletion]:
    """Get all resource completions for a user in a specific module"""
    result = await db.execute(
        select(ResourceCompletion).where(
            and_(
                ResourceCompletion.user_id == user_id,
                ResourceCompletion.module_id == module_id
            )
        )
    )
    return result.scalars().all()

async def get_user_completions_for_pathway(
    db: AsyncSession,
    user_id: UUID,
    pathway_id: str
) -> List[ResourceCompletion]:
    """Get all resource completions for a user in a pathway"""
    result = await db.execute(
        select(ResourceCompletion).where(
            and_(
                ResourceCompletion.user_id == user_id,
                ResourceCompletion.pathway_id == pathway_id
            )
        )
    )
    return result.scalars().all()

# ============================================================================
# Resource Submission CRUD Operations
# ============================================================================

async def create_resource_submission(
    db: AsyncSession,
    user_id: UUID,
    resource_id: str,
    resource_completion_id: UUID,
    file_name: str,
    file_size_bytes: int,
    file_type: str,
    gcs_bucket: str,
    gcs_path: str,
    gcs_url: str,
    upload_ip: Optional[str] = None
) -> ResourceSubmission:
    """Create a new resource submission record"""
    # Get resource to populate pathway_id and module_id
    resource = await get_resource_by_id(db, resource_id)
    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    submission = ResourceSubmission(
        user_id=user_id,
        resource_id=resource_id,
        resource_completion_id=resource_completion_id,
        file_name=file_name,
        file_size_bytes=file_size_bytes,
        file_type=file_type,
        gcs_bucket=gcs_bucket,
        gcs_path=gcs_path,
        gcs_url=gcs_url,
        submission_status='uploaded',
        upload_ip=upload_ip
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission

async def get_submission_by_id(db: AsyncSession, submission_id: UUID) -> Optional[ResourceSubmission]:
    """Get a submission by ID"""
    result = await db.execute(
        select(ResourceSubmission).where(ResourceSubmission.id == submission_id)
    )
    return result.scalar_one_or_none()

async def get_submissions_for_resource(
    db: AsyncSession,
    user_id: UUID,
    resource_id: str
) -> List[ResourceSubmission]:
    """Get all submissions for a user's resource"""
    result = await db.execute(
        select(ResourceSubmission)
        .where(
            and_(
                ResourceSubmission.user_id == user_id,
                ResourceSubmission.resource_id == resource_id,
                ResourceSubmission.deleted_at.is_(None)
            )
        )
        .order_by(ResourceSubmission.created_at.desc())
    )
    return result.scalars().all()

async def soft_delete_submission(db: AsyncSession, submission_id: UUID) -> bool:
    """Soft delete a submission"""
    await db.execute(
        update(ResourceSubmission)
        .where(ResourceSubmission.id == submission_id)
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return True

async def update_submission_review(
    db: AsyncSession,
    submission_id: UUID,
    reviewer_id: UUID,
    submission_status: str,
    grade: str,
    review_comments: Optional[str] = None
) -> ResourceSubmission:
    """Update submission with review information"""
    await db.execute(
        update(ResourceSubmission)
        .where(ResourceSubmission.id == submission_id)
        .values(
            submission_status=submission_status,
            grade=grade,
            review_comments=review_comments,
            reviewed_by=reviewer_id,
            reviewed_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()

    # Return updated submission
    result = await db.execute(
        select(ResourceSubmission).where(ResourceSubmission.id == submission_id)
    )
    return result.scalar_one()

async def get_pending_submissions(
    db: AsyncSession,
    pathway_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[int, List[dict]]:
    """Get pending submissions for instructor review"""
    # Base query
    query = (
        select(
            ResourceSubmission.id,
            ResourceSubmission.user_id,
            User.email.label('user_email'),
            User.full_name.label('user_name'),
            ResourceSubmission.resource_id,
            Resource.title.label('resource_title'),
            Resource.type.label('resource_type'),
            Resource.pathway_id,
            Resource.module_id,
            ResourceSubmission.file_name,
            ResourceSubmission.file_type,
            ResourceSubmission.file_size_bytes,
            ResourceSubmission.gcs_url,
            ResourceSubmission.submission_status,
            ResourceSubmission.created_at,
            func.extract('epoch', func.now() - ResourceSubmission.created_at).label('seconds_waiting')
        )
        .join(User, ResourceSubmission.user_id == User.id)
        .join(Resource, ResourceSubmission.resource_id == Resource.id)
        .where(
            and_(
                ResourceSubmission.submission_status == 'uploaded',
                ResourceSubmission.reviewed_at.is_(None),
                ResourceSubmission.deleted_at.is_(None)
            )
        )
    )

    # Add pathway filter if provided
    if pathway_id:
        query = query.where(Resource.pathway_id == pathway_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    # Get paginated results
    query = query.order_by(ResourceSubmission.created_at.asc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.fetchall()

    # Convert to dict list with hours_waiting
    submissions = []
    for row in rows:
        submission_dict = row._asdict()
        # Convert seconds to hours
        submission_dict['hours_waiting'] = submission_dict.pop('seconds_waiting') / 3600.0
        submissions.append(submission_dict)

    return total_count, submissions
