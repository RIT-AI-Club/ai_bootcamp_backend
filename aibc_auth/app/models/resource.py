from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, CheckConstraint, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(200), primary_key=True)
    module_id = Column(String(100), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)

    # Resource metadata
    type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Ordering and duration
    order_index = Column(Integer, nullable=False)
    duration_minutes = Column(Integer)

    # File upload configuration
    requires_upload = Column(Boolean, default=False)
    accepted_file_types = Column(ARRAY(Text))
    max_file_size_mb = Column(Integer, default=50)
    allow_resubmission = Column(Boolean, default=True)

    # External links
    url = Column(Text)

    # Metadata (quiz questions, exercise instructions, etc.)
    metadata = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('video', 'article', 'exercise', 'project', 'quiz')"),
    )

class ResourceCompletion(Base):
    __tablename__ = "resource_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(String(200), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(String(100), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="CASCADE"), nullable=False)

    # Completion status
    status = Column(String(50), default='not_started')

    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    time_spent_minutes = Column(Integer, default=0)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Submission tracking
    submission_required = Column(Boolean, default=False)
    submission_count = Column(Integer, default=0)

    # User notes and metadata
    notes = Column(Text)
    metadata = Column(JSONB)

    __table_args__ = (
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed', 'submitted', 'reviewed')"),
        CheckConstraint("progress_percentage >= 0 AND progress_percentage <= 100"),
    )

class ResourceSubmission(Base):
    __tablename__ = "resource_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(String(200), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    resource_completion_id = Column(UUID(as_uuid=True), ForeignKey("resource_completions.id", ondelete="CASCADE"), nullable=False)

    # File metadata
    file_name = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_type = Column(String(100), nullable=False)

    # Google Cloud Storage details
    gcs_bucket = Column(String(255), nullable=False)
    gcs_path = Column(Text, nullable=False)
    gcs_url = Column(Text, nullable=False)

    # Submission metadata
    submission_status = Column(String(50), default='uploaded')
    upload_ip = Column(Text)

    # Review and grading
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    review_comments = Column(Text)
    grade = Column(String(10))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Additional metadata
    metadata = Column(JSONB)

    __table_args__ = (
        CheckConstraint("submission_status IN ('uploading', 'uploaded', 'processing', 'approved', 'rejected', 'failed')"),
        CheckConstraint("grade IN ('pass', 'fail') OR grade IS NULL"),
    )
