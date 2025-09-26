from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime, date
from uuid import UUID

# Pathway schemas
class PathwayBase(BaseModel):
    id: str
    slug: str
    title: str
    short_title: str
    instructor: str
    color: str
    total_modules: int = 0

class PathwayResponse(PathwayBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Module schemas
class ModuleBase(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    order_index: int
    duration_minutes: Optional[int] = None

class ModuleResponse(ModuleBase):
    pathway_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ModuleWithCompletion(ModuleResponse):
    completed: bool = False
    completed_at: Optional[datetime] = None

# User Progress schemas
class UserProgressBase(BaseModel):
    pathway_id: str
    progress_percentage: int = Field(ge=0, le=100)
    completed_modules: int = 0
    total_time_spent_minutes: int = 0

class UserProgressCreate(BaseModel):
    pathway_id: str

class UserProgressUpdate(BaseModel):
    current_module_id: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    completed_modules: Optional[int] = None
    total_time_spent_minutes: Optional[int] = None

class UserProgressResponse(UserProgressBase):
    id: UUID
    user_id: UUID
    current_module_id: Optional[str] = None
    started_at: datetime
    last_accessed_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Module Completion schemas
class ModuleCompletionCreate(BaseModel):
    module_id: str
    pathway_id: str
    time_spent_minutes: Optional[int] = 0

class ModuleCompletionResponse(BaseModel):
    id: UUID
    user_id: UUID
    pathway_id: str
    module_id: str
    completed_at: datetime
    time_spent_minutes: int

    class Config:
        from_attributes = True

# Achievement schemas
class AchievementBase(BaseModel):
    id: str
    name: str
    description: str
    icon: Optional[str] = None
    category: str
    requirement_type: str
    requirement_value: Optional[int] = None

class AchievementResponse(AchievementBase):
    created_at: datetime

    class Config:
        from_attributes = True

class UserAchievementResponse(BaseModel):
    achievement: AchievementResponse
    earned_at: datetime

    class Config:
        from_attributes = True

# Learning Streak schemas
class LearningStreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# Aggregated responses
class PathwayProgressResponse(BaseModel):
    pathway: PathwayResponse
    progress: UserProgressResponse
    modules: List[ModuleWithCompletion]
    next_module: Optional[ModuleResponse] = None

class UserProgressSummary(BaseModel):
    user_id: UUID
    total_pathways: int = 0
    pathways_started: int = 0
    pathways_completed: int = 0
    total_modules_completed: int = 0
    total_time_spent_minutes: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    achievements_earned: int = 0
    pathway_progress: List[UserProgressResponse] = []

class DashboardData(BaseModel):
    user_id: UUID
    pathways: List[Dict[str, any]]
    summary: UserProgressSummary
    recent_achievements: List[UserAchievementResponse] = []
    streak: Optional[LearningStreakResponse] = None