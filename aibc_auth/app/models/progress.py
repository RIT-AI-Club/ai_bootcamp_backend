from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class Pathway(Base):
    __tablename__ = "pathways"

    id = Column(String(100), primary_key=True)
    slug = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    short_title = Column(String(100), nullable=False)
    instructor = Column(String(255), nullable=False)
    color = Column(String(100), nullable=False)
    total_modules = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Module(Base):
    __tablename__ = "modules"

    id = Column(String(100), primary_key=True)
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)
    duration_minutes = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    current_module_id = Column(String(100), ForeignKey("modules.id", ondelete="SET NULL"))
    progress_percentage = Column(Integer, default=0)
    completed_modules = Column(Integer, default=0)
    total_time_spent_minutes = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint('progress_percentage >= 0 AND progress_percentage <= 100'),
    )

class ModuleCompletion(Base):
    __tablename__ = "module_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(String(100), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    time_spent_minutes = Column(Integer, default=0)

    # Instructor approval fields
    approval_status = Column(String(50), default='pending')
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    review_comments = Column(Text)

    __table_args__ = (
        CheckConstraint("approval_status IN ('pending', 'approved', 'rejected')"),
    )

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(100))
    category = Column(String(50), nullable=False)
    requirement_type = Column(String(50), nullable=False)
    requirement_value = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(String(100), ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

class LearningStreak(Base):
    __tablename__ = "learning_streaks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())