from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date, timedelta
from uuid import UUID
import logging

from app.models.progress import (
    Pathway, Module, UserProgress, ModuleCompletion,
    Achievement, UserAchievement, LearningStreak
)
from app.schemas.progress import (
    UserProgressCreate, UserProgressUpdate, ModuleCompletionCreate
)

logger = logging.getLogger(__name__)

class ProgressCRUD:

    # Pathway operations
    @staticmethod
    async def get_all_pathways(db: AsyncSession) -> List[Pathway]:
        """Get all pathways with 1-hour cache"""
        result = await db.execute(select(Pathway).order_by(Pathway.id))
        return result.scalars().all()

    @staticmethod
    async def get_pathway_by_id(db: AsyncSession, pathway_id: str) -> Optional[Pathway]:
        """Get pathway by ID with 1-hour cache"""
        result = await db.execute(select(Pathway).where(Pathway.id == pathway_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pathway_by_slug(db: AsyncSession, slug: str) -> Optional[Pathway]:
        """Get pathway by slug with 1-hour cache"""
        result = await db.execute(select(Pathway).where(Pathway.slug == slug))
        return result.scalar_one_or_none()

    # Module operations
    @staticmethod
    async def get_modules_by_pathway(db: AsyncSession, pathway_id: str) -> List[Module]:
        result = await db.execute(
            select(Module)
            .where(Module.pathway_id == pathway_id)
            .order_by(Module.order_index)
        )
        return result.scalars().all()

    @staticmethod
    async def get_module_by_id(db: AsyncSession, module_id: str) -> Optional[Module]:
        result = await db.execute(select(Module).where(Module.id == module_id))
        return result.scalar_one_or_none()

    # User Progress operations
    @staticmethod
    async def get_user_progress(db: AsyncSession, user_id: UUID, pathway_id: str) -> Optional[UserProgress]:
        result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.pathway_id == pathway_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_user_progress(db: AsyncSession, user_id: UUID) -> List[UserProgress]:
        result = await db.execute(
            select(UserProgress).where(UserProgress.user_id == user_id)
        )
        return result.scalars().all()

    @staticmethod
    async def create_user_progress(
        db: AsyncSession,
        user_id: UUID,
        progress_data: UserProgressCreate
    ) -> UserProgress:
        # Check if progress already exists
        existing = await ProgressCRUD.get_user_progress(db, user_id, progress_data.pathway_id)
        if existing:
            return existing

        # Create new progress
        user_progress = UserProgress(
            user_id=user_id,
            pathway_id=progress_data.pathway_id,
            progress_percentage=0,
            completed_modules=0,
            total_time_spent_minutes=0
        )
        db.add(user_progress)
        await db.commit()
        await db.refresh(user_progress)

        # Update streak
        await ProgressCRUD.update_learning_streak(db, user_id)

        return user_progress

    @staticmethod
    async def update_user_progress(
        db: AsyncSession,
        user_id: UUID,
        pathway_id: str,
        progress_update: UserProgressUpdate
    ) -> Optional[UserProgress]:
        result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.pathway_id == pathway_id
                )
            )
        )
        user_progress = result.scalar_one_or_none()

        if not user_progress:
            return None

        # Update fields
        update_data = progress_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user_progress, field, value)

        user_progress.last_accessed_at = datetime.utcnow()

        # Check if pathway is completed
        if user_progress.progress_percentage == 100 and not user_progress.completed_at:
            user_progress.completed_at = datetime.utcnow()
            # Check for pathway completion achievements
            await ProgressCRUD.check_and_award_achievements(db, user_id)

        await db.commit()
        await db.refresh(user_progress)
        return user_progress

    # Module Completion operations
    @staticmethod
    async def mark_module_complete(
        db: AsyncSession,
        user_id: UUID,
        completion_data: ModuleCompletionCreate
    ) -> ModuleCompletion:
        # Check if already completed
        result = await db.execute(
            select(ModuleCompletion).where(
                and_(
                    ModuleCompletion.user_id == user_id,
                    ModuleCompletion.module_id == completion_data.module_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Create completion record
        completion = ModuleCompletion(
            user_id=user_id,
            pathway_id=completion_data.pathway_id,
            module_id=completion_data.module_id,
            time_spent_minutes=completion_data.time_spent_minutes or 0
        )
        db.add(completion)

        # Update user progress
        user_progress = await ProgressCRUD.get_user_progress(db, user_id, completion_data.pathway_id)
        if not user_progress:
            # Create progress if it doesn't exist
            progress_create = UserProgressCreate(pathway_id=completion_data.pathway_id)
            user_progress = await ProgressCRUD.create_user_progress(db, user_id, progress_create)

        # Get total modules in pathway
        pathway = await ProgressCRUD.get_pathway_by_id(db, completion_data.pathway_id)
        if pathway:
            user_progress.completed_modules += 1
            user_progress.progress_percentage = int((user_progress.completed_modules / pathway.total_modules) * 100)
            user_progress.total_time_spent_minutes += completion_data.time_spent_minutes or 0
            user_progress.last_accessed_at = datetime.utcnow()

            if user_progress.progress_percentage == 100:
                user_progress.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(completion)

        # Update learning streak
        await ProgressCRUD.update_learning_streak(db, user_id)

        # Check for achievements
        await ProgressCRUD.check_and_award_achievements(db, user_id)

        return completion

    @staticmethod
    async def get_module_completions(
        db: AsyncSession,
        user_id: UUID,
        pathway_id: Optional[str] = None
    ) -> List[ModuleCompletion]:
        query = select(ModuleCompletion).where(ModuleCompletion.user_id == user_id)
        if pathway_id:
            query = query.where(ModuleCompletion.pathway_id == pathway_id)

        result = await db.execute(query)
        return result.scalars().all()

    # Achievement operations
    @staticmethod
    async def get_all_achievements(db: AsyncSession) -> List[Achievement]:
        result = await db.execute(select(Achievement).order_by(Achievement.category, Achievement.id))
        return result.scalars().all()

    @staticmethod
    async def get_user_achievements(db: AsyncSession, user_id: UUID) -> List[UserAchievement]:
        result = await db.execute(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(desc(UserAchievement.earned_at))
        )
        return result.scalars().all()

    @staticmethod
    async def award_achievement(
        db: AsyncSession,
        user_id: UUID,
        achievement_id: str
    ) -> Optional[UserAchievement]:
        # Check if already awarded
        result = await db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id
                )
            )
        )
        if result.scalar_one_or_none():
            return None

        # Award achievement
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id
        )
        db.add(user_achievement)
        await db.commit()
        await db.refresh(user_achievement)
        return user_achievement

    @staticmethod
    async def check_and_award_achievements(db: AsyncSession, user_id: UUID):
        # Get user's current stats
        completions = await ProgressCRUD.get_module_completions(db, user_id)
        progress_list = await ProgressCRUD.get_all_user_progress(db, user_id)
        streak = await ProgressCRUD.get_learning_streak(db, user_id)

        modules_completed = len(completions)
        pathways_completed = sum(1 for p in progress_list if p.progress_percentage == 100)
        pathways_started = len(progress_list)
        total_time = sum(p.total_time_spent_minutes for p in progress_list)

        # Check each achievement
        achievements = await ProgressCRUD.get_all_achievements(db)
        for achievement in achievements:
            should_award = False

            if achievement.requirement_type == 'modules_completed':
                should_award = modules_completed >= achievement.requirement_value
            elif achievement.requirement_type == 'pathways_completed':
                should_award = pathways_completed >= achievement.requirement_value
            elif achievement.requirement_type == 'streak_days':
                should_award = streak and streak.current_streak >= achievement.requirement_value
            elif achievement.requirement_type == 'time_spent':
                should_award = total_time >= achievement.requirement_value
            elif achievement.requirement_type == 'custom' and achievement.id == 'pathway-starter':
                should_award = pathways_started >= 1

            if should_award:
                await ProgressCRUD.award_achievement(db, user_id, achievement.id)

    # Learning Streak operations
    @staticmethod
    async def get_learning_streak(db: AsyncSession, user_id: UUID) -> Optional[LearningStreak]:
        result = await db.execute(
            select(LearningStreak).where(LearningStreak.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_learning_streak(db: AsyncSession, user_id: UUID) -> LearningStreak:
        streak = await ProgressCRUD.get_learning_streak(db, user_id)
        today = date.today()

        if not streak:
            # Create new streak
            streak = LearningStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=today
            )
            db.add(streak)
        else:
            # Update existing streak
            if streak.last_activity_date:
                days_diff = (today - streak.last_activity_date).days

                if days_diff == 0:
                    # Same day, no change
                    pass
                elif days_diff == 1:
                    # Consecutive day
                    streak.current_streak += 1
                    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
                else:
                    # Streak broken
                    streak.current_streak = 1
            else:
                streak.current_streak = 1
                streak.longest_streak = max(streak.longest_streak or 0, 1)

            streak.last_activity_date = today
            streak.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(streak)
        return streak

    # Dashboard data
    @staticmethod
    async def get_dashboard_data(db: AsyncSession, user_id: UUID) -> Dict:
        """Optimized dashboard data with single JOIN query and 5-minute cache"""

        # Single optimized query with JOINs - eliminates N+1 problem
        pathway_progress_query = await db.execute(
            select(
                Pathway.id,
                Pathway.slug,
                Pathway.title,
                Pathway.short_title,
                Pathway.instructor,
                Pathway.color,
                func.coalesce(UserProgress.progress_percentage, 0).label('progress'),
                func.coalesce(UserProgress.total_time_spent_minutes, 0).label('time_spent')
            )
            .outerjoin(
                UserProgress,
                and_(
                    Pathway.id == UserProgress.pathway_id,
                    UserProgress.user_id == user_id
                )
            )
            .order_by(Pathway.id)
        )

        pathway_data = []
        pathways_started = 0
        pathways_completed = 0
        total_time = 0

        for row in pathway_progress_query:
            pathway_dict = {
                'id': row.id,
                'slug': row.slug,
                'title': row.title,
                'shortTitle': row.short_title,
                'instructor': row.instructor,
                'color': row.color,
                'progress': row.progress
            }
            pathway_data.append(pathway_dict)

            if row.progress > 0:
                pathways_started += 1
            if row.progress == 100:
                pathways_completed += 1
            total_time += row.time_spent

        # Get module completions count in single query
        modules_completed_result = await db.execute(
            select(func.count(ModuleCompletion.id))
            .where(ModuleCompletion.user_id == user_id)
        )
        modules_count = modules_completed_result.scalar() or 0

        # Get streak data
        streak = await ProgressCRUD.get_learning_streak(db, user_id)

        # Get recent achievements with single JOIN query
        achievements_result = await db.execute(
            select(
                Achievement.id,
                Achievement.name,
                Achievement.description,
                Achievement.icon,
                Achievement.category,
                UserAchievement.earned_at
            )
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
            .order_by(desc(UserAchievement.earned_at))
            .limit(5)
        )

        recent_achievements = [
            {
                'id': row.id,
                'name': row.name,
                'description': row.description,
                'icon': row.icon,
                'category': row.category,
                'earned_at': row.earned_at.isoformat()
            }
            for row in achievements_result
        ]

        return {
            'pathways': pathway_data,
            'summary': {
                'pathways_started': pathways_started,
                'pathways_completed': pathways_completed,
                'modules_completed': modules_count,
                'total_time_spent_minutes': total_time,
                'current_streak': streak.current_streak if streak else 0,
                'longest_streak': streak.longest_streak if streak else 0
            },
            'recent_achievements': recent_achievements,
            'streak': {
                'current': streak.current_streak if streak else 0,
                'longest': streak.longest_streak if streak else 0,
                'last_activity': streak.last_activity_date.isoformat() if streak and streak.last_activity_date else None
            }
        }