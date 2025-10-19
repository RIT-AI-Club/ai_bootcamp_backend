"""
Email helper for admin dashboard (Flask app)
Provides sync wrappers around async email service
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def send_module_approved_email_sync(
    user_email: str,
    user_name: str,
    module_title: str,
    pathway_title: str,
    pathway_id: str,
    reviewer_name: str = "Instructor"
) -> bool:
    """
    Synchronous wrapper to send module approved email from Flask
    """
    try:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aibc_auth'))

        from app.core.email import email_service
        from app.core.config import settings
        from jinja2 import Environment, FileSystemLoader
        from premailer import transform as inline_css
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Check if email notifications enabled
        if not settings.EMAIL_NOTIFICATIONS_ENABLED or not settings.SEND_STUDENT_NOTIFICATIONS:
            logger.info("Email notifications disabled")
            return False

        # Validate SMTP credentials
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return False

        # Render template
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'aibc_auth', 'app', 'templates', 'emails')
        env = Environment(loader=FileSystemLoader(template_dir))

        context = {
            'user_name': user_name,
            'module_title': module_title,
            'pathway_title': pathway_title,
            'approved_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'reviewer_name': reviewer_name,
            'next_module': None,
            'dashboard_url': f"{settings.FRONTEND_URL}/pathway/{pathway_id}",
            'settings': settings
        }

        # Render HTML
        html_template = env.get_template('module_approved.html')
        html_content = html_template.render(**context)
        html_content = inline_css(html_content)

        # Render text
        try:
            text_template = env.get_template('module_approved.txt')
            text_content = text_template.render(**context)
        except:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)

        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = f"✅ Module Approved: {module_title}"
        message['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message['To'] = user_email

        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        message.attach(part1)
        message.attach(part2)

        # Send via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

        logger.info(f"Approval email sent to {user_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")
        return False


def send_module_rejected_email_sync(
    user_email: str,
    user_name: str,
    resource_title: str,
    module_title: str,
    pathway_id: str,
    feedback: str
) -> bool:
    """
    Synchronous wrapper to send module rejected email from Flask
    """
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aibc_auth'))

        from app.core.config import settings
        from jinja2 import Environment, FileSystemLoader
        from premailer import transform as inline_css
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        if not settings.EMAIL_NOTIFICATIONS_ENABLED or not settings.SEND_STUDENT_NOTIFICATIONS:
            logger.info("Email notifications disabled")
            return False

        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return False

        # Render template
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'aibc_auth', 'app', 'templates', 'emails')
        env = Environment(loader=FileSystemLoader(template_dir))

        context = {
            'user_name': user_name,
            'resource_title': resource_title,
            'module_title': module_title,
            'feedback': feedback,
            'module_url': f"{settings.FRONTEND_URL}/pathway/{pathway_id}",
            'settings': settings
        }

        html_template = env.get_template('module_rejected.html')
        html_content = html_template.render(**context)
        html_content = inline_css(html_content)

        try:
            text_template = env.get_template('module_rejected.txt')
            text_content = text_template.render(**context)
        except:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)

        message = MIMEMultipart('alternative')
        message['Subject'] = f"📝 Revision Requested: {resource_title}"
        message['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message['To'] = user_email

        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        message.attach(part1)
        message.attach(part2)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

        logger.info(f"Rejection email sent to {user_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send rejection email: {e}")
        return False
