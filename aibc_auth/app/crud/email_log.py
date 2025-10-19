from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.models.email_log import EmailLog

async def create_email_log(
    db: AsyncSession,
    recipient_email: str,
    email_type: str,
    subject: str,
    template_name: str,
    context_data: Dict[str, Any],
    user_id: Optional[UUID] = None,
    module_id: Optional[str] = None,
    pathway_id: Optional[str] = None,
    resource_submission_id: Optional[UUID] = None,
    module_completion_id: Optional[UUID] = None
) -> EmailLog:
    """Create email log entry for auditing and retry logic"""
    email_log = EmailLog(
        recipient_email=recipient_email,
        recipient_user_id=user_id,
        email_type=email_type,
        subject=subject,
        template_name=template_name,
        context_data=context_data,
        module_id=module_id,
        pathway_id=pathway_id,
        resource_submission_id=resource_submission_id,
        module_completion_id=module_completion_id,
        status='pending'
    )
    db.add(email_log)
    await db.commit()
    await db.refresh(email_log)
    return email_log

async def update_email_status(
    db: AsyncSession,
    log_id: UUID,
    status: str,
    error_message: Optional[str] = None,
    increment_retry: bool = False
) -> EmailLog:
    """Update email delivery status"""
    update_values = {
        "status": status,
        "updated_at": datetime.now(timezone.utc)
    }

    if status == 'sent':
        update_values["sent_at"] = datetime.now(timezone.utc)
    elif status == 'failed':
        update_values["failed_at"] = datetime.now(timezone.utc)
        if error_message:
            update_values["error_message"] = error_message

    await db.execute(
        update(EmailLog)
        .where(EmailLog.id == log_id)
        .values(**update_values)
    )

    if increment_retry:
        await db.execute(
            update(EmailLog)
            .where(EmailLog.id == log_id)
            .values(retry_count=EmailLog.retry_count + 1)
        )

    await db.commit()

    # Return updated log
    result = await db.execute(
        select(EmailLog).where(EmailLog.id == log_id)
    )
    return result.scalar_one()

async def get_failed_emails(
    db: AsyncSession,
    max_retries: int = 3,
    limit: int = 100
) -> List[EmailLog]:
    """Get failed emails for retry processing"""
    result = await db.execute(
        select(EmailLog)
        .where(
            and_(
                EmailLog.status == 'failed',
                EmailLog.retry_count < max_retries
            )
        )
        .order_by(EmailLog.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()

async def get_email_log_by_id(
    db: AsyncSession,
    log_id: UUID
) -> Optional[EmailLog]:
    """Get email log by ID"""
    result = await db.execute(
        select(EmailLog).where(EmailLog.id == log_id)
    )
    return result.scalar_one_or_none()
