from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from app.db.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.crud.progress import ProgressCRUD
from app.schemas.progress import (
    PathwayResponse,
    ModuleResponse,
    ModuleWithCompletion,
    UserProgressResponse,
    UserProgressCreate,
    UserProgressUpdate,
    ModuleCompletionCreate,
    ModuleCompletionResponse,
    ModuleApprovalRequest,
    PathwayProgressResponse,
    UserProgressSummary,
    DashboardData,
    AchievementResponse,
    UserAchievementResponse,
    LearningStreakResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["progress"]
)

# Pathway endpoints
@router.get("/pathways", response_model=List[PathwayResponse])
async def get_pathways(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pathways = await ProgressCRUD.get_all_pathways(db)
    return pathways

@router.get("/pathways/{pathway_slug}", response_model=PathwayProgressResponse)
async def get_pathway_progress(
    pathway_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get pathway by slug
    pathway = await ProgressCRUD.get_pathway_by_slug(db, pathway_slug)
    if not pathway:
        raise HTTPException(status_code=404, detail="Pathway not found")

    # Get user progress
    user_progress = await ProgressCRUD.get_user_progress(db, current_user.id, pathway.id)
    if not user_progress:
        # Create new progress entry if it doesn't exist
        progress_data = UserProgressCreate(pathway_id=pathway.id)
        user_progress = await ProgressCRUD.create_user_progress(db, current_user.id, progress_data)

    # Get modules
    modules = await ProgressCRUD.get_modules_by_pathway(db, pathway.id)

    # Get user's module completions
    completions = await ProgressCRUD.get_module_completions(db, current_user.id, pathway.id)
    completion_map = {c.module_id: c for c in completions}

    # Build modules with completion status and approval status
    modules_with_completion = []
    next_module = None
    for module in modules:
        completion = completion_map.get(module.id)
        completed = completion is not None
        module_dict = ModuleWithCompletion(
            id=module.id,
            pathway_id=module.pathway_id,
            title=module.title,
            description=module.description,
            order_index=module.order_index,
            duration_minutes=module.duration_minutes,
            created_at=module.created_at,
            updated_at=module.updated_at,
            completed=completed,
            completed_at=completion.completed_at if completion else None,
            approval_status=completion.approval_status if completion else None
        )
        modules_with_completion.append(module_dict)

        # Find next module to complete (only approved ones count as complete)
        if not completed or (completion and completion.approval_status != 'approved'):
            if not next_module:
                next_module = module

    return PathwayProgressResponse(
        pathway=pathway,
        progress=user_progress,
        modules=modules_with_completion,
        next_module=next_module
    )

# User Progress endpoints
@router.get("/user/summary", response_model=UserProgressSummary)
async def get_user_progress_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        progress_list = await ProgressCRUD.get_all_user_progress(db, current_user.id)
        completions = await ProgressCRUD.get_module_completions(db, current_user.id)
        streak = await ProgressCRUD.get_learning_streak(db, current_user.id)
        achievements = await ProgressCRUD.get_user_achievements(db, current_user.id)

        # Calculate summary stats
        pathways_started = len(progress_list) if progress_list else 0
        pathways_completed = sum(1 for p in progress_list if p.progress_percentage == 100) if progress_list else 0
        total_modules = len(completions) if completions else 0
        total_time = sum(p.total_time_spent_minutes for p in progress_list) if progress_list else 0

        return UserProgressSummary(
            user_id=current_user.id,
            total_pathways=13,  # Total pathways available
            pathways_started=pathways_started,
            pathways_completed=pathways_completed,
            total_modules_completed=total_modules,
            total_time_spent_minutes=total_time,
            current_streak=streak.current_streak if streak else 0,
            longest_streak=streak.longest_streak if streak else 0,
            achievements_earned=len(achievements) if achievements else 0,
            pathway_progress=progress_list if progress_list else []
        )
    except Exception as e:
        logger.error(f"Error fetching user progress summary: {e}")
        # Return default empty summary for new users
        return UserProgressSummary(
            user_id=current_user.id,
            total_pathways=13,
            pathways_started=0,
            pathways_completed=0,
            total_modules_completed=0,
            total_time_spent_minutes=0,
            current_streak=0,
            longest_streak=0,
            achievements_earned=0,
            pathway_progress=[]
        )

@router.get("/user/dashboard")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        dashboard_data = await ProgressCRUD.get_dashboard_data(db, current_user.id)
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        # Return default empty dashboard for new users
        return {
            "pathways": [],
            "summary": {
                "pathways_started": 0,
                "pathways_completed": 0,
                "modules_completed": 0,
                "total_time_spent_minutes": 0,
                "current_streak": 0,
                "longest_streak": 0
            },
            "recent_achievements": []
        }

@router.get("/debug/tables")
async def debug_tables(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Debug endpoint to check table contents"""
    try:
        pathways = await ProgressCRUD.get_all_pathways(db)

        # Get modules for first pathway if it exists
        modules = []
        if pathways:
            modules = await ProgressCRUD.get_modules_by_pathway(db, pathways[0].id)

        return {
            "pathways_count": len(pathways),
            "pathways": [{"id": p.id, "slug": p.slug, "title": p.title} for p in pathways[:3]],
            "modules_count": len(modules),
            "modules": [{"id": m.id, "title": m.title, "pathway_id": m.pathway_id} for m in modules[:3]],
            "database_connected": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "database_connected": False
        }

@router.post("/debug/seed-data")
async def seed_basic_data(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Temporary endpoint to seed basic pathway and module data if missing"""
    try:
        from sqlalchemy import text

        # Check if pathways exist
        pathways = await ProgressCRUD.get_all_pathways(db)
        if len(pathways) > 0:
            return {"message": "Data already exists", "pathways_count": len(pathways)}

        # Insert basic pathway data
        pathway_sql = """
        INSERT INTO pathways (id, slug, title, short_title, instructor, color, module_count) VALUES
        ('ai-agents', 'ai-agents', 'AI Agents (MCP, Tooling)', 'AI Agents', 'Olivier', 'from-sky-500 to-blue-500', 9),
        ('deep-learning', 'deep-learning', 'Deep Learning Foundations', 'Deep Learning', 'Sarah', 'from-purple-500 to-pink-500', 12);
        """

        # Insert AI Agents modules that are missing
        module_sql = """
        INSERT INTO modules (id, pathway_id, title, description, order_index, duration_minutes) VALUES
        ('agent-fundamentals', 'ai-agents', 'AI Agent Fundamentals', 'Understanding agent architectures and the foundations of autonomous AI systems.', 1, 50),
        ('mcp-protocol', 'ai-agents', 'Model Context Protocol (MCP)', 'Deep dive into MCP for building standardized agent-tool interactions.', 2, 75),
        ('tool-integration', 'ai-agents', 'Tool Integration & APIs', 'Connect agents with external services, databases, and APIs for expanded capabilities.', 3, 60),
        ('multi-agent-systems', 'ai-agents', 'Multi-Agent Systems', 'Design and coordinate multiple agents working together on complex tasks.', 4, 80),
        ('agent-deployment', 'ai-agents', 'Agent Deployment & Production', 'Deploy and scale AI agents in production environments.', 5, 90)
        ON CONFLICT (id) DO NOTHING;
        """

        await db.execute(text(pathway_sql))
        await db.execute(text(module_sql))
        await db.commit()

        # Verify seeding worked
        pathways = await ProgressCRUD.get_all_pathways(db)
        return {
            "message": "Basic data seeded successfully",
            "pathways_count": len(pathways)
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding data: {e}")
        return {"error": str(e)}

@router.get("/user/dashboard-optimized")
async def get_dashboard_complete(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Production-optimized single endpoint for complete dashboard data.
    Eliminates multiple API calls by combining dashboard, summary, and pathway data.
    Uses optimized JOIN queries and 5-minute caching.
    """
    try:
        # Single call to optimized dashboard data
        dashboard_data = await ProgressCRUD.get_dashboard_data(db, current_user.id)

        # Add user summary for compatibility
        user_summary = {
            "user_id": current_user.id,
            "total_pathways": len(dashboard_data["pathways"]),
            "pathways_started": dashboard_data["summary"]["pathways_started"],
            "pathways_completed": dashboard_data["summary"]["pathways_completed"],
            "total_modules_completed": dashboard_data["summary"]["modules_completed"],
            "total_time_spent_minutes": dashboard_data["summary"]["total_time_spent_minutes"],
            "current_streak": dashboard_data["summary"]["current_streak"],
            "longest_streak": dashboard_data["summary"]["longest_streak"],
            "achievements_earned": len(dashboard_data["recent_achievements"]),
            "pathway_progress": []  # Empty for performance, data already in pathways
        }

        return {
            "dashboard": dashboard_data,
            "summary": user_summary,
            "pathways": dashboard_data["pathways"],  # Direct access for PathwayGrid
            "achievements": dashboard_data["recent_achievements"],
            "streak": dashboard_data["streak"]
        }

    except Exception as e:
        logger.error(f"Error fetching optimized dashboard: {e}")
        # Return empty data structure on error
        return {
            "dashboard": {
                "pathways": [],
                "summary": {
                    "pathways_started": 0,
                    "pathways_completed": 0,
                    "modules_completed": 0,
                    "total_time_spent_minutes": 0,
                    "current_streak": 0,
                    "longest_streak": 0
                },
                "recent_achievements": [],
                "streak": {"current": 0, "longest": 0, "last_activity": None}
            },
            "summary": {
                "user_id": current_user.id,
                "total_pathways": 0,
                "pathways_started": 0,
                "pathways_completed": 0,
                "total_modules_completed": 0,
                "total_time_spent_minutes": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "achievements_earned": 0,
                "pathway_progress": []
            },
            "pathways": [],
            "achievements": [],
            "streak": {"current": 0, "longest": 0, "last_activity": None}
        }

@router.post("/user/start-pathway", response_model=UserProgressResponse)
async def start_pathway(
    progress_data: UserProgressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if pathway exists
    pathway = await ProgressCRUD.get_pathway_by_id(db, progress_data.pathway_id)
    if not pathway:
        raise HTTPException(status_code=404, detail="Pathway not found")

    # Create or get existing progress
    user_progress = await ProgressCRUD.create_user_progress(db, current_user.id, progress_data)
    return user_progress

@router.put("/user/pathway/{pathway_slug}", response_model=UserProgressResponse)
async def update_pathway_progress(
    pathway_slug: str,
    progress_update: UserProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get pathway by slug to get the ID
    pathway = await ProgressCRUD.get_pathway_by_slug(db, pathway_slug)
    if not pathway:
        raise HTTPException(status_code=404, detail="Pathway not found")

    user_progress = await ProgressCRUD.update_user_progress(
        db, current_user.id, pathway.id, progress_update
    )
    if not user_progress:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return user_progress

# Module Completion endpoints
@router.post("/modules/complete", response_model=ModuleCompletionResponse)
async def mark_module_complete(
    completion_data: ModuleCompletionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        from app.crud import resource as resource_crud

        logger.info(f"Attempting to mark module complete: {completion_data.module_id} for user: {current_user.id}")

        # Verify module exists
        module = await ProgressCRUD.get_module_by_id(db, completion_data.module_id)
        if not module:
            logger.warning(f"Module not found: {completion_data.module_id}")
            raise HTTPException(status_code=404, detail=f"Module not found: {completion_data.module_id}")

        # Verify pathway exists
        pathway = await ProgressCRUD.get_pathway_by_id(db, completion_data.pathway_id)
        if not pathway:
            logger.warning(f"Pathway not found: {completion_data.pathway_id}")
            raise HTTPException(status_code=404, detail=f"Pathway not found: {completion_data.pathway_id}")

        # VALIDATION: Check all resources are completed
        resources = await resource_crud.get_resources_by_module(db, completion_data.module_id)

        if resources:  # Only validate if module has resources
            completions = await resource_crud.get_user_completions_for_module(db, current_user.id, completion_data.module_id)
            completion_map = {c.resource_id: c for c in completions}

            # Check each resource
            incomplete_resources = []
            missing_uploads = []

            for resource in resources:
                completion = completion_map.get(resource.id)

                # Check if resource is completed
                if not completion or completion.status not in ['completed', 'submitted', 'reviewed']:
                    incomplete_resources.append(resource.title)
                    continue

                # Check if upload is required and submitted
                if resource.requires_upload and completion.submission_count == 0:
                    missing_uploads.append(resource.title)

            if incomplete_resources:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot complete module: The following resources must be completed first: {', '.join(incomplete_resources)}"
                )

            if missing_uploads:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot complete module: The following resources require file submission: {', '.join(missing_uploads)}"
                )

            logger.info(f"All {len(resources)} resources completed for module {completion_data.module_id}")

        # Mark as complete (will be in 'pending' approval status by default)
        completion = await ProgressCRUD.mark_module_complete(db, current_user.id, completion_data)
        logger.info(f"Module marked complete (pending review): {completion.id}")
        return completion

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking module complete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/modules/completions", response_model=List[ModuleCompletionResponse])
async def get_user_completions(
    pathway_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    completions = await ProgressCRUD.get_module_completions(db, current_user.id, pathway_id)
    return completions

@router.post("/modules/{completion_id}/approve", response_model=ModuleCompletionResponse)
async def approve_module_completion(
    completion_id: UUID,
    approval_request: ModuleApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint to approve or reject a module completion.
    Requires admin/instructor role.
    """
    try:
        from datetime import datetime, timezone
        from sqlalchemy import update, select
        from app.models.progress import ModuleCompletion

        # TODO: Add admin role check when role system is implemented
        # For now, any authenticated user can approve (will be restricted later)

        # Get the completion record
        result = await db.execute(
            select(ModuleCompletion).where(ModuleCompletion.id == completion_id)
        )
        completion = result.scalar_one_or_none()

        if not completion:
            raise HTTPException(status_code=404, detail="Module completion not found")

        # Update approval status
        await db.execute(
            update(ModuleCompletion)
            .where(ModuleCompletion.id == completion_id)
            .values(
                approval_status=approval_request.approval_status,
                reviewed_by=current_user.id,
                reviewed_at=datetime.now(timezone.utc),
                review_comments=approval_request.review_comments
            )
        )
        await db.commit()

        # Fetch updated completion
        result = await db.execute(
            select(ModuleCompletion).where(ModuleCompletion.id == completion_id)
        )
        updated_completion = result.scalar_one()

        logger.info(f"Module completion {completion_id} {approval_request.approval_status} by {current_user.email}")

        return ModuleCompletionResponse.model_validate(updated_completion)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error approving module completion: {e}")
        raise HTTPException(status_code=500, detail="Failed to update approval status")

@router.get("/modules/pending-reviews")
async def get_pending_module_reviews(
    pathway_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin endpoint to get all pending module reviews.
    Returns modules waiting for instructor approval.
    """
    try:
        from sqlalchemy import select, func, and_
        from app.models.progress import ModuleCompletion, Module, Pathway
        from app.models.user import User as UserModel

        # TODO: Add admin role check

        # Build query for pending reviews
        query = (
            select(
                ModuleCompletion.id,
                ModuleCompletion.user_id,
                UserModel.email.label('user_email'),
                UserModel.full_name.label('user_name'),
                ModuleCompletion.pathway_id,
                Pathway.title.label('pathway_title'),
                ModuleCompletion.module_id,
                Module.title.label('module_title'),
                ModuleCompletion.completed_at,
                func.extract('epoch', func.now() - ModuleCompletion.completed_at).label('seconds_waiting')
            )
            .join(UserModel, ModuleCompletion.user_id == UserModel.id)
            .join(Pathway, ModuleCompletion.pathway_id == Pathway.id)
            .join(Module, ModuleCompletion.module_id == Module.id)
            .where(
                and_(
                    ModuleCompletion.approval_status == 'pending',
                    ModuleCompletion.completed_at.isnot(None)
                )
            )
        )

        if pathway_id:
            query = query.where(ModuleCompletion.pathway_id == pathway_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_pending = count_result.scalar()

        # Get paginated results
        query = query.order_by(ModuleCompletion.completed_at.asc()).limit(limit).offset(offset)
        result = await db.execute(query)
        rows = result.fetchall()

        # Format results
        pending_reviews = []
        for row in rows:
            pending_reviews.append({
                'id': str(row.id),
                'user_id': str(row.user_id),
                'user_email': row.user_email,
                'user_name': row.user_name or 'Unknown',
                'pathway_id': row.pathway_id,
                'pathway_title': row.pathway_title,
                'module_id': row.module_id,
                'module_title': row.module_title,
                'completed_at': row.completed_at.isoformat(),
                'hours_waiting': row.seconds_waiting / 3600.0 if row.seconds_waiting else 0
            })

        return {
            'total_pending': total_pending,
            'reviews': pending_reviews,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"Error fetching pending reviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending reviews")

# Achievement endpoints
@router.get("/achievements")
async def get_all_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    achievements = await ProgressCRUD.get_all_achievements(db)
    user_achievements = await ProgressCRUD.get_user_achievements(db, current_user.id)

    # Create a set of earned achievement IDs
    earned_ids = {ua.achievement_id for ua in user_achievements}

    # Build response with earned status
    result = []
    for achievement in achievements:
        result.append({
            'id': achievement.id,
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'category': achievement.category,
            'requirement_type': achievement.requirement_type,
            'requirement_value': achievement.requirement_value,
            'earned': achievement.id in earned_ids,
            'earned_at': next((ua.earned_at for ua in user_achievements if ua.achievement_id == achievement.id), None)
        })

    return result

@router.get("/achievements/user")
async def get_user_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    user_achievements = await ProgressCRUD.get_user_achievements(db, current_user.id)
    achievements = await ProgressCRUD.get_all_achievements(db)

    # Create achievement map
    achievement_map = {a.id: a for a in achievements}

    # Build response
    result = []
    for ua in user_achievements:
        achievement = achievement_map.get(ua.achievement_id)
        if achievement:
            result.append({
                'achievement': {
                    'id': achievement.id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'category': achievement.category
                },
                'earned_at': ua.earned_at
            })

    return result

# Learning Streak endpoints
@router.get("/streak", response_model=LearningStreakResponse)
async def get_learning_streak(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    streak = await ProgressCRUD.get_learning_streak(db, current_user.id)
    if not streak:
        # Return default values if no streak exists
        from datetime import datetime, timezone
        return LearningStreakResponse(
            current_streak=0,
            longest_streak=0,
            last_activity_date=None,
            updated_at=datetime.now(timezone.utc)
        )
    return streak