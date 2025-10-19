from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Recipient information
    recipient_email = Column(String(255), nullable=False)
    recipient_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    # Email metadata
    email_type = Column(String(100), nullable=False)
    subject = Column(String(500), nullable=False)
    template_name = Column(String(200))

    # Email status
    status = Column(String(50), default='pending')
    sent_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Context data
    context_data = Column(JSONB)

    # Reference to related entities
    module_id = Column(String(100), ForeignKey("modules.id", ondelete="SET NULL"))
    pathway_id = Column(String(100), ForeignKey("pathways.id", ondelete="SET NULL"))
    resource_submission_id = Column(UUID(as_uuid=True), ForeignKey("resource_submissions.id", ondelete="SET NULL"))
    module_completion_id = Column(UUID(as_uuid=True), ForeignKey("module_completions.id", ondelete="SET NULL"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'bounced')"),
    )
