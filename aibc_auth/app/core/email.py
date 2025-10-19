"""
Production-grade async email service with SMTP support, retry logic, and template rendering
"""
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from premailer import transform as inline_css
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import email_log as email_log_crud

logger = logging.getLogger(__name__)

class EmailService:
    """Async SMTP email service with retry logic and template rendering"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from_email = settings.SMTP_FROM_EMAIL
        self.smtp_from_name = settings.SMTP_FROM_NAME
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.retry_attempts = settings.EMAIL_RETRY_ATTEMPTS
        self.retry_delay = settings.EMAIL_RETRY_DELAY_SECONDS

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        template_dir.mkdir(parents=True, exist_ok=True)

        self.template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def _get_smtp_config(self) -> dict:
        """Get SMTP configuration"""
        return {
            "hostname": self.smtp_host,
            "port": self.smtp_port,
            "username": self.smtp_username,
            "password": self.smtp_password,
            "use_tls": False,  # Don't use direct TLS
            "start_tls": self.smtp_use_tls,  # Use STARTTLS instead
            "timeout": 30
        }

    def render_template(self, template_name: str, context: dict) -> tuple[str, str]:
        """
        Render HTML and plain text versions of email template
        Returns (html_content, text_content)
        """
        try:
            # Render HTML template
            html_template = self.template_env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context, settings=settings)

            # Inline CSS for better email client compatibility
            html_content = inline_css(html_content)

            # Render plain text template
            try:
                text_template = self.template_env.get_template(f"{template_name}.txt")
                text_content = text_template.render(**context, settings=settings)
            except TemplateNotFound:
                # Fallback: strip HTML tags for plain text
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text(separator='\n', strip=True)

            return html_content, text_content

        except TemplateNotFound:
            logger.error(f"Email template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Error rendering email template {template_name}: {e}")
            raise

    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        db: Optional[AsyncSession] = None,
        cc: Optional[List[str]] = None,
        log_metadata: Optional[dict] = None
    ) -> bool:
        """
        Send email using template with retry logic
        Returns True if sent successfully, False otherwise
        """
        # Check if email notifications are enabled
        if not settings.EMAIL_NOTIFICATIONS_ENABLED:
            logger.info(f"Email notifications disabled. Would have sent: {subject} to {to_email}")
            return False

        # Validate SMTP credentials
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email not sent.")
            return False

        # Create email log entry if db session provided
        email_log_id = None
        if db and log_metadata:
            try:
                email_log = await email_log_crud.create_email_log(
                    db=db,
                    recipient_email=to_email,
                    email_type=log_metadata.get('email_type', 'unknown'),
                    subject=subject,
                    template_name=template_name,
                    context_data=context,
                    user_id=log_metadata.get('user_id'),
                    module_id=log_metadata.get('module_id'),
                    pathway_id=log_metadata.get('pathway_id'),
                    resource_submission_id=log_metadata.get('resource_submission_id'),
                    module_completion_id=log_metadata.get('module_completion_id')
                )
                email_log_id = email_log.id
            except Exception as e:
                logger.error(f"Failed to create email log: {e}")

        # Render email content
        try:
            html_content, text_content = self.render_template(template_name, context)
        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            if db and email_log_id:
                await email_log_crud.update_email_status(
                    db, email_log_id, 'failed', str(e)
                )
            return False

        # Create MIME message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
        message['To'] = to_email

        if cc:
            message['Cc'] = ', '.join(cc)

        # Attach plain text and HTML versions
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        message.attach(part1)
        message.attach(part2)

        # Send email with retry logic
        recipients = [to_email]
        if cc:
            recipients.extend(cc)

        for attempt in range(self.retry_attempts):
            try:
                async with aiosmtplib.SMTP(**self._get_smtp_config()) as smtp:
                    await smtp.send_message(message)

                logger.info(f"Email sent successfully to {to_email}: {subject}")

                # Update email log status
                if db and email_log_id:
                    await email_log_crud.update_email_status(db, email_log_id, 'sent')

                return True

            except (aiosmtplib.SMTPException, asyncio.TimeoutError, ConnectionError) as e:
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    # Wait before retrying with exponential backoff
                    wait_time = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed
                    logger.error(f"Email send failed after {self.retry_attempts} attempts: {e}")

                    if db and email_log_id:
                        await email_log_crud.update_email_status(
                            db, email_log_id, 'failed', str(e), increment_retry=True
                        )

                    return False

        return False

    async def send_module_approved(
        self,
        db: AsyncSession,
        user_id: UUID,
        user_email: str,
        user_name: str,
        module_id: str,
        module_title: str,
        pathway_id: str,
        pathway_title: str,
        approved_date: datetime,
        reviewer_name: str = "Instructor",
        next_module: Optional[dict] = None
    ) -> bool:
        """Send module approved notification to student"""
        if not settings.SEND_STUDENT_NOTIFICATIONS:
            return False

        context = {
            'user_name': user_name,
            'module_title': module_title,
            'pathway_title': pathway_title,
            'approved_date': approved_date.strftime('%B %d, %Y at %I:%M %p'),
            'reviewer_name': reviewer_name,
            'next_module': next_module,
            'dashboard_url': f"{settings.FRONTEND_URL}/pathway/{pathway_id}"
        }

        log_metadata = {
            'email_type': 'module_approved',
            'user_id': user_id,
            'module_id': module_id,
            'pathway_id': pathway_id
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"✅ Module Approved: {module_title}",
            template_name='module_approved',
            context=context,
            db=db,
            log_metadata=log_metadata
        )

    async def send_module_rejected(
        self,
        db: AsyncSession,
        user_id: UUID,
        user_email: str,
        user_name: str,
        resource_id: str,
        resource_title: str,
        module_id: str,
        module_title: str,
        pathway_id: str,
        feedback: str,
        resource_submission_id: Optional[UUID] = None
    ) -> bool:
        """Send module rejected/revision requested notification to student"""
        if not settings.SEND_STUDENT_NOTIFICATIONS:
            return False

        context = {
            'user_name': user_name,
            'resource_title': resource_title,
            'module_title': module_title,
            'feedback': feedback,
            'module_url': f"{settings.FRONTEND_URL}/pathway/{pathway_id}"
        }

        log_metadata = {
            'email_type': 'module_rejected',
            'user_id': user_id,
            'module_id': module_id,
            'pathway_id': pathway_id,
            'resource_submission_id': resource_submission_id
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"📝 Revision Requested: {resource_title}",
            template_name='module_rejected',
            context=context,
            db=db,
            log_metadata=log_metadata
        )

    async def send_module_submitted_to_admins(
        self,
        db: AsyncSession,
        user_id: UUID,
        student_email: str,
        student_name: str,
        module_id: str,
        module_title: str,
        pathway_id: str,
        pathway_title: str,
        submission_date: datetime,
        resources_pending: List[dict],
        student_progress: dict,
        module_completion_id: Optional[UUID] = None
    ) -> bool:
        """Notify admins of new module submission"""
        if not settings.SEND_ADMIN_NOTIFICATIONS:
            return False

        admin_emails = settings.get_admin_emails()
        if not admin_emails:
            logger.warning("No admin emails configured for notifications")
            return False

        context = {
            'student_name': student_name,
            'student_email': student_email,
            'pathway_title': pathway_title,
            'module_title': module_title,
            'submission_date': submission_date.strftime('%B %d, %Y at %I:%M %p'),
            'resources_count': len(resources_pending),
            'resources_pending': resources_pending,
            'student_progress': student_progress,
            'admin_dashboard_url': f"{settings.FRONTEND_URL.replace('www.', 'admin.')}/submissions"
        }

        log_metadata = {
            'email_type': 'module_submitted',
            'user_id': user_id,
            'module_id': module_id,
            'pathway_id': pathway_id,
            'module_completion_id': module_completion_id
        }

        # Send to all admin emails
        success = True
        for admin_email in admin_emails:
            result = await self.send_email(
                to_email=admin_email,
                subject=f"📋 New Module Submission: {module_title} by {student_name}",
                template_name='module_submitted',
                context=context,
                db=db,
                log_metadata=log_metadata
            )
            success = success and result

        return success

    async def send_resource_resubmitted_to_admins(
        self,
        db: AsyncSession,
        user_id: UUID,
        student_email: str,
        student_name: str,
        resource_id: str,
        resource_title: str,
        module_id: str,
        module_title: str,
        pathway_id: str,
        pathway_title: str,
        resubmission_date: datetime,
        file_name: str,
        file_size_bytes: int,
        file_type: str,
        submission_count: int,
        previous_feedback: str,
        student_progress: dict,
        resource_submission_id: Optional[UUID] = None
    ) -> bool:
        """Notify admins when student resubmits a previously rejected resource"""
        if not settings.SEND_ADMIN_NOTIFICATIONS:
            return False

        admin_emails = settings.get_admin_emails()
        if not admin_emails:
            logger.warning("No admin emails configured for notifications")
            return False

        context = {
            'student_name': student_name,
            'student_email': student_email,
            'resource_title': resource_title,
            'module_title': module_title,
            'pathway_title': pathway_title,
            'resubmission_date': resubmission_date.strftime('%B %d, %Y at %I:%M %p'),
            'file_name': file_name,
            'file_size_mb': round(file_size_bytes / 1024 / 1024, 2),
            'file_type': file_type,
            'submission_count': submission_count,
            'previous_feedback': previous_feedback,
            'student_progress': student_progress,
            'admin_dashboard_url': f"{settings.FRONTEND_URL.replace('www.', 'admin.')}/submissions"
        }

        log_metadata = {
            'email_type': 'resource_resubmitted',
            'user_id': user_id,
            'module_id': module_id,
            'pathway_id': pathway_id,
            'resource_submission_id': resource_submission_id
        }

        # Send to all admin emails
        success = True
        for admin_email in admin_emails:
            result = await self.send_email(
                to_email=admin_email,
                subject=f"🔄 Resubmission: {resource_title} by {student_name}",
                template_name='resource_resubmitted',
                context=context,
                db=db,
                log_metadata=log_metadata
            )
            success = success and result

        return success

# Singleton instance
email_service = EmailService()
