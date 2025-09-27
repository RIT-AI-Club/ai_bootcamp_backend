from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

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
    PathwayProgressResponse,
    UserProgressSummary,
    DashboardData,
    AchievementResponse,
    UserAchievementResponse,
    LearningStreakResponse
)

router = APIRouter(
    prefix="/api/v1/progress",
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

@router.get("/pathways/{pathway_id}", response_model=PathwayProgressResponse)
async def get_pathway_progress(
    pathway_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get pathway
    pathway = await ProgressCRUD.get_pathway_by_id(db, pathway_id)
    if not pathway:
        raise HTTPException(status_code=404, detail="Pathway not found")

    # Get user progress
    user_progress = await ProgressCRUD.get_user_progress(db, current_user.id, pathway_id)
    if not user_progress:
        # Create new progress entry if it doesn't exist
        progress_data = UserProgressCreate(pathway_id=pathway_id)
        user_progress = await ProgressCRUD.create_user_progress(db, current_user.id, progress_data)

    # Get modules
    modules = await ProgressCRUD.get_modules_by_pathway(db, pathway_id)

    # Get user's module completions
    completions = await ProgressCRUD.get_module_completions(db, current_user.id, pathway_id)
    completion_set = {c.module_id for c in completions}

    # Build modules with completion status
    modules_with_completion = []
    next_module = None
    for module in modules:
        completed = module.id in completion_set
        module_dict = ModuleWithCompletion(
            id=module.id,
            pathway_id=module.pathway_id,
            title=module.title,
            description=module.description,
            order_index=module.order_index,
            duration_minutes=module.duration_minutes,
            created_at=module.created_at,
            updated_at=module.updated_at,
            completed=completed
        )
        modules_with_completion.append(module_dict)

        # Find next module to complete
        if not completed and not next_module:
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
    progress_list = await ProgressCRUD.get_all_user_progress(db, current_user.id)
    completions = await ProgressCRUD.get_module_completions(db, current_user.id)
    streak = await ProgressCRUD.get_learning_streak(db, current_user.id)
    achievements = await ProgressCRUD.get_user_achievements(db, current_user.id)

    # Calculate summary stats
    pathways_started = len(progress_list)
    pathways_completed = sum(1 for p in progress_list if p.progress_percentage == 100)
    total_modules = len(completions)
    total_time = sum(p.total_time_spent_minutes for p in progress_list)

    return UserProgressSummary(
        user_id=current_user.id,
        total_pathways=13,  # Total pathways available
        pathways_started=pathways_started,
        pathways_completed=pathways_completed,
        total_modules_completed=total_modules,
        total_time_spent_minutes=total_time,
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        achievements_earned=len(achievements),
        pathway_progress=progress_list
    )

@router.get("/user/dashboard")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    dashboard_data = await ProgressCRUD.get_dashboard_data(db, current_user.id)
    return dashboard_data

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

@router.put("/user/pathway/{pathway_id}", response_model=UserProgressResponse)
async def update_pathway_progress(
    pathway_id: str,
    progress_update: UserProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_progress = await ProgressCRUD.update_user_progress(
        db, current_user.id, pathway_id, progress_update
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
    # Verify module exists
    module = await ProgressCRUD.get_module_by_id(db, completion_data.module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Mark as complete
    completion = await ProgressCRUD.mark_module_complete(db, current_user.id, completion_data)
    return completion

@router.get("/modules/completions", response_model=List[ModuleCompletionResponse])
async def get_user_completions(
    pathway_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    completions = await ProgressCRUD.get_module_completions(db, current_user.id, pathway_id)
    return completions

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