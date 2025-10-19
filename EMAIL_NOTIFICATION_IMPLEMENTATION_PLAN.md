# Email Notification System - Implementation Plan

## Overview

Add production-grade email notifications for module submission and approval workflows using SMTP. This system will notify students when their modules are approved/rejected and alert admins when modules are submitted for review.

---

## Architecture Design

### Email Service Layer
**Location:** `aibc_auth/app/core/email.py`

```python
# EmailService class with async support
# - SMTP connection management with connection pooling
# - Template rendering engine (Jinja2)
# - Retry logic with exponential backoff
# - Rate limiting to prevent spam
# - Email queue for async delivery
# - HTML + plain text fallback emails
```

### Email Templates
**Location:** `aibc_auth/app/templates/emails/`

```
emails/
├── base.html                    # Base template with branding
├── module_approved.html         # Student: Module approved
├── module_rejected.html         # Student: Module needs revision
├── module_submitted.html        # Admin: New module to review
└── resource_reviewed.html       # Student: Individual resource feedback
```

---

## Email Notification Triggers

### 1. Student Notifications

#### Module Approved
**Trigger:** Admin approves last resource → auto-approval sets `module_completions.approval_status = 'approved'`
**Location:** `aibc_auth/app/api/v1/resources.py:847-863` and `admin_dashboard/app.py:807-820`
**Recipients:** Student (`users.email`)
**Template:** `module_approved.html`
**Data:**
- Student name (`users.full_name`)
- Module title (`modules.title`)
- Pathway title (`pathways.title`)
- Completion date (`module_completions.reviewed_at`)
- Next module recommendation
- Dashboard link

#### Module Rejected
**Trigger:** Admin rejects a resource submission
**Location:** `admin_dashboard/app.py:707-741` (after review submission)
**Recipients:** Student (`users.email`)
**Template:** `module_rejected.html`
**Data:**
- Student name
- Module title
- Pathway title
- Rejected resource title (`resources.title`)
- Instructor feedback (`resource_submissions.review_comments`)
- Re-submission instructions
- Module dashboard link

#### Individual Resource Reviewed (Optional Enhancement)
**Trigger:** Admin approves/rejects any resource submission
**Location:** `aibc_auth/app/api/v1/resources.py:747-873`
**Recipients:** Student
**Template:** `resource_reviewed.html`
**Data:**
- Resource title and type
- Review status (approved/rejected)
- Instructor comments
- Grade (pass/fail)

### 2. Admin Notifications

#### Module Submitted for Review
**Trigger:** User clicks "Submit for Review" → creates `module_completions` with `approval_status = 'pending'`
**Location:** `aibc_auth/app/api/v1/progress.py:350-419` (after successful module completion)
**Recipients:** Admin email(s) from configuration (`romanslack1@gmail.com` + configurable list)
**Template:** `module_submitted.html`
**Data:**
- Student name and email
- Module title and pathway
- Submission timestamp
- Number of resources requiring review
- List of uploaded files
- Admin dashboard review link
- Student's progress summary (modules completed in pathway)

---

## Configuration Changes

### Environment Variables
**Files:** `.env`, `.env.production`

```bash
# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=AI Bootcamp <noreply@aiclub-bootcamp.com>
SMTP_FROM_NAME=AI Bootcamp

# Admin Notification Recipients (comma-separated)
ADMIN_EMAILS=romanslack1@gmail.com,admin2@example.com

# Email Feature Flags
EMAIL_NOTIFICATIONS_ENABLED=true
SEND_STUDENT_NOTIFICATIONS=true
SEND_ADMIN_NOTIFICATIONS=true

# Email Rate Limiting
EMAIL_RATE_LIMIT_PER_HOUR=50
EMAIL_RETRY_ATTEMPTS=3
EMAIL_RETRY_DELAY_SECONDS=60
```

### Config Class Updates
**File:** `aibc_auth/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # SMTP Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@aiclub-bootcamp.com"
    SMTP_FROM_NAME: str = "AI Bootcamp"
    SMTP_USE_TLS: bool = True

    # Admin Recipients
    ADMIN_EMAILS: str = "romanslack1@gmail.com"

    # Email Feature Flags
    EMAIL_NOTIFICATIONS_ENABLED: bool = True
    SEND_STUDENT_NOTIFICATIONS: bool = True
    SEND_ADMIN_NOTIFICATIONS: bool = True
    EMAIL_RATE_LIMIT_PER_HOUR: int = 50
    EMAIL_RETRY_ATTEMPTS: int = 3
    EMAIL_RETRY_DELAY_SECONDS: int = 60

    def get_admin_emails(self) -> List[str]:
        return [email.strip() for email in self.ADMIN_EMAILS.split(",")]
```

---

## Database Changes

### Email Logs Table (Optional but Recommended)
**Migration:** `migrations/002_add_email_notifications.sql`

```sql
-- Track all sent emails for auditing and debugging
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_email VARCHAR(255) NOT NULL,
    recipient_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email_type VARCHAR(100) NOT NULL,  -- 'module_approved', 'module_rejected', 'module_submitted', etc.
    subject VARCHAR(500) NOT NULL,
    template_name VARCHAR(200),

    -- Email status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'bounced')),
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Context data (JSON for flexibility)
    context_data JSONB,

    -- Reference to related entities
    module_id VARCHAR(100) REFERENCES modules(id) ON DELETE SET NULL,
    pathway_id VARCHAR(100) REFERENCES pathways(id) ON DELETE SET NULL,
    resource_submission_id UUID REFERENCES resource_submissions(id) ON DELETE SET NULL,
    module_completion_id UUID REFERENCES module_completions(id) ON DELETE SET NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_email_logs_recipient ON email_logs(recipient_email);
CREATE INDEX idx_email_logs_status ON email_logs(status);
CREATE INDEX idx_email_logs_type ON email_logs(email_type);
CREATE INDEX idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX idx_email_logs_user_id ON email_logs(recipient_user_id);

-- Trigger for updated_at
CREATE TRIGGER update_email_logs_updated_at BEFORE UPDATE ON email_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### User Preferences (Future Enhancement)
```sql
-- Add email preference fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_module_approval BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_module_rejection BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_resource_review BOOLEAN DEFAULT TRUE;
```

---

## Dependencies

### Python Packages
**File:** `aibc_auth/requirements.txt`

```txt
# Add these lines:
aiosmtplib==3.0.1              # Async SMTP client
jinja2==3.1.2                  # Template engine
premailer==3.10.0              # Inline CSS for email compatibility
beautifulsoup4==4.12.2         # HTML parsing for premailer
```

### Admin Dashboard Dependencies
**File:** `admin_dashboard/requirements.txt`

```txt
# Add if not present:
jinja2==3.1.2
aiosmtplib==3.0.1
```

---

## Implementation Structure

### 1. Core Email Service
**File:** `aibc_auth/app/core/email.py`

```python
class EmailService:
    """Async SMTP email service with retry logic and template rendering"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        # Connection pool, rate limiter, retry logic

    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        cc: List[str] = None,
        attachments: List[dict] = None
    ) -> bool:
        """Send email using template with retry logic"""
        pass

    async def send_module_approved(self, user_id: UUID, module_id: str):
        """Send module approved notification to student"""
        pass

    async def send_module_rejected(self, user_id: UUID, module_id: str, resource_id: str, feedback: str):
        """Send module rejected notification to student"""
        pass

    async def send_module_submitted_to_admins(self, user_id: UUID, module_id: str):
        """Notify admins of new module submission"""
        pass

    def render_template(self, template_name: str, context: dict) -> tuple[str, str]:
        """Render HTML and plain text versions of email template"""
        pass

# Singleton instance
email_service = EmailService()
```

### 2. Email Template Renderer
**File:** `aibc_auth/app/core/email_templates.py`

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

template_env = Environment(
    loader=FileSystemLoader("app/templates/emails"),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_email_template(template_name: str, context: dict) -> tuple[str, str]:
    """Returns (html_content, text_content)"""
    html_template = template_env.get_template(f"{template_name}.html")
    text_template = template_env.get_template(f"{template_name}.txt")

    html_content = html_template.render(**context)
    text_content = text_template.render(**context)

    # Inline CSS for email clients
    html_content = premailer.transform(html_content)

    return html_content, text_content
```

### 3. Database Service for Email Logs
**File:** `aibc_auth/app/crud/email_logs.py`

```python
async def create_email_log(
    db: AsyncSession,
    recipient_email: str,
    email_type: str,
    subject: str,
    template_name: str,
    context_data: dict,
    user_id: UUID = None,
    module_id: str = None,
    pathway_id: str = None
) -> EmailLog:
    """Create email log entry for auditing"""
    pass

async def update_email_status(
    db: AsyncSession,
    log_id: UUID,
    status: str,
    error_message: str = None
):
    """Update email delivery status"""
    pass

async def get_failed_emails(db: AsyncSession, limit: int = 100) -> List[EmailLog]:
    """Get failed emails for retry processing"""
    pass
```

---

## Code Integration Points

### FastAPI Backend Integration

#### 1. Module Auto-Approval (Student Notification)
**File:** `aibc_auth/app/api/v1/resources.py`
**Line:** After 860 (after auto-approval UPDATE query)

```python
# After auto-approval succeeds
if all_resources_approved:
    await db.execute(...)  # Existing UPDATE
    await db.commit()
    logger.info(f"Auto-approved module {resource.module_id}")

    # NEW: Send approval email to student
    try:
        await email_service.send_module_approved(
            user_id=submission.user_id,
            module_id=resource.module_id
        )
    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")
        # Don't fail the request - email is non-critical
```

#### 2. Resource Rejection (Student Notification)
**File:** `aibc_auth/app/api/v1/resources.py`
**Line:** After 774 (after review submission update)

```python
# After updating submission review
updated = await resource_crud.update_submission_review(...)

# NEW: Send rejection email if rejected
if review.submission_status == 'rejected':
    try:
        await email_service.send_resource_rejected(
            user_id=submission.user_id,
            resource_id=submission.resource_id,
            module_id=resource.module_id,
            feedback=review.review_comments or "Please review and resubmit."
        )
    except Exception as e:
        logger.error(f"Failed to send rejection email: {e}")
```

#### 3. Module Submission (Admin Notification)
**File:** `aibc_auth/app/api/v1/progress.py`
**Line:** After 411 (after module completion creation)

```python
# After successful module completion
completion = await ProgressCRUD.mark_module_complete(db, current_user.id, completion_data)
logger.info(f"Module marked complete (pending review): {completion.id}")

# NEW: Notify admins
try:
    await email_service.send_module_submitted_to_admins(
        user_id=current_user.id,
        module_id=completion_data.module_id,
        pathway_id=completion_data.pathway_id
    )
except Exception as e:
    logger.error(f"Failed to send admin notification: {e}")

return completion
```

### Admin Dashboard Integration

#### 1. Module Auto-Approval (Student Notification)
**File:** `admin_dashboard/app.py`
**Line:** After 815 (after auto-approval in Flask)

```python
# After auto-approval
if all_approved:
    cur.execute("UPDATE module_completions SET approval_status = 'approved' ...")
    print(f"[AUTO-APPROVE] Module {module_id} auto-approved!")

    # NEW: Send email notification
    try:
        import asyncio
        from email_service import send_module_approved_email

        asyncio.run(send_module_approved_email(
            user_id=user_id,
            module_id=module_id,
            user_email=submission['user_email'],  # From query
            user_name=submission['user_name']
        ))
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send approval email: {e}")
```

#### 2. Resource Review (Student Notification)
**File:** `admin_dashboard/app.py`
**Line:** After 741 (after review update)

```python
# After updating submission
cur.execute("UPDATE resource_submissions SET submission_status = %s ...")

# NEW: Send notification for rejection
if data['submission_status'] == 'rejected':
    try:
        import asyncio
        from email_service import send_resource_rejected_email

        asyncio.run(send_resource_rejected_email(
            user_id=user_id,
            resource_id=submission['resource_id'],
            module_id=module_id,
            user_email=submission['user_email'],
            user_name=submission['user_name'],
            feedback=data.get('review_comments', '')
        ))
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send rejection email: {e}")
```

---

## Email Templates Design

### Base Template Structure
**File:** `aibc_auth/app/templates/emails/base.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Inline-friendly CSS */
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .container { max-width: 600px; margin: 0 auto; background: #ffffff; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center; }
        .content { padding: 40px 30px; color: #333333; line-height: 1.6; }
        .button { display: inline-block; background: #667eea; color: #ffffff; padding: 14px 28px; border-radius: 6px; text-decoration: none; }
        .footer { padding: 20px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="color: #ffffff; margin: 0;">🚀 AI Bootcamp</h1>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        <div class="footer">
            <p>© 2025 AI Bootcamp. All rights reserved.</p>
            <p><a href="{{ settings.FRONTEND_URL }}/help">Help</a> | <a href="{{ settings.FRONTEND_URL }}/dashboard">Dashboard</a></p>
        </div>
    </div>
</body>
</html>
```

### Module Approved Template
**File:** `aibc_auth/app/templates/emails/module_approved.html`

```html
{% extends "base.html" %}
{% block content %}
<h2 style="color: #10b981;">✅ Module Approved!</h2>

<p>Hi {{ user_name }},</p>

<p>Congratulations! Your submission for <strong>{{ module_title }}</strong> in the <strong>{{ pathway_title }}</strong> pathway has been approved by your instructor.</p>

<div style="background: #f0fdf4; border-left: 4px solid #10b981; padding: 16px; margin: 24px 0;">
    <p style="margin: 0; color: #166534;"><strong>✓ All resources reviewed and approved</strong></p>
    <p style="margin: 8px 0 0 0; color: #166534; font-size: 14px;">You can now proceed to the next module.</p>
</div>

<p><strong>Module Details:</strong></p>
<ul>
    <li>Pathway: {{ pathway_title }}</li>
    <li>Module: {{ module_title }}</li>
    <li>Approved: {{ approved_date }}</li>
    <li>Reviewed by: {{ reviewer_name }}</li>
</ul>

{% if next_module %}
<p><strong>Next up:</strong> {{ next_module.title }}</p>
{% endif %}

<p style="margin-top: 32px;">
    <a href="{{ dashboard_url }}" class="button">View Your Progress</a>
</p>

<p style="margin-top: 24px; color: #666666; font-size: 14px;">Keep up the great work! 🎉</p>
{% endblock %}
```

### Module Rejected Template
**File:** `aibc_auth/app/templates/emails/module_rejected.html`

```html
{% extends "base.html" %}
{% block content %}
<h2 style="color: #ef4444;">📝 Revision Requested</h2>

<p>Hi {{ user_name }},</p>

<p>Your instructor has reviewed your submission for <strong>{{ resource_title }}</strong> in <strong>{{ module_title }}</strong> and is requesting some revisions.</p>

<div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin: 24px 0;">
    <p style="margin: 0; color: #991b1b;"><strong>Instructor Feedback:</strong></p>
    <p style="margin: 8px 0 0 0; color: #991b1b;">{{ feedback }}</p>
</div>

<p><strong>What to do next:</strong></p>
<ol>
    <li>Review the instructor's feedback carefully</li>
    <li>Make the requested changes to your submission</li>
    <li>Re-upload your revised work</li>
    <li>Wait for the next review</li>
</ol>

<p style="margin-top: 32px;">
    <a href="{{ module_url }}" class="button">Revise Submission</a>
</p>

<p style="margin-top: 24px; color: #666666; font-size: 14px;">Don't worry - revisions are a normal part of the learning process! 💪</p>
{% endblock %}
```

### Admin Module Submission Notification
**File:** `aibc_auth/app/templates/emails/module_submitted.html`

```html
{% extends "base.html" %}
{% block content %}
<h2 style="color: #3b82f6;">📋 New Module Submission</h2>

<p>A student has submitted a module for review.</p>

<div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; margin: 24px 0;">
    <p style="margin: 0;"><strong>Student:</strong> {{ student_name }} ({{ student_email }})</p>
    <p style="margin: 8px 0 0 0;"><strong>Pathway:</strong> {{ pathway_title }}</p>
    <p style="margin: 8px 0 0 0;"><strong>Module:</strong> {{ module_title }}</p>
    <p style="margin: 8px 0 0 0;"><strong>Submitted:</strong> {{ submission_date }}</p>
</div>

<p><strong>Resources to Review ({{ resources_count }}):</strong></p>
<ul>
{% for resource in resources_pending %}
    <li>{{ resource.type|title }}: {{ resource.title }}</li>
{% endfor %}
</ul>

<p><strong>Student Progress:</strong></p>
<ul>
    <li>Modules completed: {{ student_progress.completed_modules }}</li>
    <li>Pathway progress: {{ student_progress.pathway_progress }}%</li>
    <li>Total time spent: {{ student_progress.total_time_hours }}h</li>
</ul>

<p style="margin-top: 32px;">
    <a href="{{ admin_dashboard_url }}" class="button">Review Submission</a>
</p>

<p style="margin-top: 24px; color: #666666; font-size: 14px;">Please review within 48 hours to maintain student momentum.</p>
{% endblock %}
```

### Plain Text Versions
**Files:** `*.txt` for each HTML template

```
Module Approved - Plain Text Example:

AI Bootcamp - Module Approved
===============================

Hi {{ user_name }},

Congratulations! Your submission for "{{ module_title }}" in the {{ pathway_title }} pathway has been approved.

Module Details:
- Pathway: {{ pathway_title }}
- Module: {{ module_title }}
- Approved: {{ approved_date }}

View your progress: {{ dashboard_url }}

Keep up the great work!

---
© 2025 AI Bootcamp
```

---

## Error Handling & Resilience

### Retry Strategy
```python
# Exponential backoff for failed emails
RETRY_SCHEDULE = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour

async def send_with_retry(email_data: dict, max_retries: int = 4):
    for attempt in range(max_retries):
        try:
            await smtp_client.send_message(email_data)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_SCHEDULE[attempt])
            else:
                logger.error(f"Email failed after {max_retries} attempts: {e}")
                return False
```

### Graceful Degradation
```python
# Email sending should NEVER block critical operations
try:
    await email_service.send_module_approved(user_id, module_id)
except Exception as e:
    logger.error(f"Email notification failed: {e}")
    # Continue processing - email is non-critical
    # Log to email_logs table with status='failed'
```

### Rate Limiting
```python
# Prevent email spam
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Max 50 emails per hour per service
@limiter.limit("50/hour")
async def send_email(...):
    pass
```

---

## Security Considerations

### 1. SMTP Authentication
- Use app-specific passwords for Gmail (not account password)
- Store credentials in environment variables or secret manager
- Use TLS encryption (port 587)

### 2. Email Content Sanitization
- Escape all user-generated content in templates
- Validate email addresses before sending
- Prevent email header injection

### 3. Privacy
- Don't include sensitive data in emails (passwords, tokens, etc.)
- Include unsubscribe links for compliance
- Log email activities for audit trails

### 4. Spam Prevention
- Rate limit email sending
- Use proper email headers (SPF, DKIM, DMARC)
- Include organization branding

---

## Monitoring & Observability

### Logging
```python
# Structured logging for email events
logger.info("Email sent", extra={
    "email_type": "module_approved",
    "recipient": user_email,
    "module_id": module_id,
    "sent_at": datetime.utcnow(),
    "smtp_response": smtp_response
})
```

### Metrics to Track
- Email delivery success rate
- Average email send time
- Failed email count by type
- Retry attempts distribution
- Bounce/complaint rates

### Admin Dashboard Enhancement
Add email logs view:
- Recent emails sent
- Failed emails with retry status
- Email delivery statistics
- Filter by user, type, status

---

## SMTP Provider Recommendations

### Option 1: Gmail SMTP (Development & Small Scale)
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-specific-password  # Generate in Google Account settings
```
**Limits:** 500 emails/day
**Cost:** Free

### Option 2: SendGrid (Production Recommended)
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```
**Limits:** 100 emails/day (free), 40k/month (paid)
**Cost:** Free tier, $15+/month for paid
**Benefits:** Better deliverability, analytics, templates

### Option 3: Amazon SES (Cost-Effective Production)
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-username
SMTP_PASSWORD=your-ses-password
```
**Limits:** 62k emails/month (free tier with EC2)
**Cost:** $0.10 per 1,000 emails
**Benefits:** Scalable, reliable, cheap for high volume

### Option 4: Mailgun
```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=your-mailgun-username
SMTP_PASSWORD=your-mailgun-password
```
**Limits:** 5k emails/month (free)
**Cost:** $35/month for 50k emails
**Benefits:** Developer-friendly API, good docs

---

## File Structure Summary

```
ai_bootcamp_backend/
├── aibc_auth/
│   ├── app/
│   │   ├── core/
│   │   │   ├── email.py                    # NEW: Email service
│   │   │   ├── email_templates.py          # NEW: Template renderer
│   │   │   └── config.py                   # MODIFY: Add email settings
│   │   ├── crud/
│   │   │   └── email_logs.py               # NEW: Email log CRUD
│   │   ├── models/
│   │   │   └── email_log.py                # NEW: EmailLog model
│   │   ├── schemas/
│   │   │   └── email.py                    # NEW: Email schemas
│   │   ├── api/v1/
│   │   │   ├── resources.py                # MODIFY: Add email triggers
│   │   │   └── progress.py                 # MODIFY: Add email triggers
│   │   └── templates/
│   │       └── emails/                     # NEW: Email template directory
│   │           ├── base.html
│   │           ├── base.txt
│   │           ├── module_approved.html
│   │           ├── module_approved.txt
│   │           ├── module_rejected.html
│   │           ├── module_rejected.txt
│   │           ├── module_submitted.html
│   │           └── module_submitted.txt
│   ├── requirements.txt                    # MODIFY: Add email dependencies
│   └── .env                                # MODIFY: Add email config
├── admin_dashboard/
│   ├── app.py                              # MODIFY: Add email triggers
│   ├── email_service.py                    # NEW: Shared email helper
│   └── requirements.txt                    # MODIFY: Add email dependencies
├── migrations/
│   └── 002_add_email_notifications.sql     # NEW: Email logs table
└── EMAIL_NOTIFICATION_IMPLEMENTATION_PLAN.md  # THIS FILE
```

---

## Configuration Example

### `.env` File Example
```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=aibootcamp@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=AI Bootcamp <noreply@aiclub-bootcamp.com>
SMTP_FROM_NAME=AI Bootcamp
SMTP_USE_TLS=true

# Admin notification recipients (comma-separated)
ADMIN_EMAILS=romanslack1@gmail.com,instructor@aiclub.com

# Feature flags
EMAIL_NOTIFICATIONS_ENABLED=true
SEND_STUDENT_NOTIFICATIONS=true
SEND_ADMIN_NOTIFICATIONS=true

# Rate limiting
EMAIL_RATE_LIMIT_PER_HOUR=50
EMAIL_RETRY_ATTEMPTS=3
EMAIL_RETRY_DELAY_SECONDS=60
```

---

## Summary of Changes

### New Files (9)
1. `aibc_auth/app/core/email.py` - Core email service
2. `aibc_auth/app/core/email_templates.py` - Template renderer
3. `aibc_auth/app/crud/email_logs.py` - Email log CRUD
4. `aibc_auth/app/models/email_log.py` - Email log model
5. `aibc_auth/app/schemas/email.py` - Email schemas
6. `aibc_auth/app/templates/emails/*` - 7 template files (HTML + TXT)
7. `admin_dashboard/email_service.py` - Flask email helper
8. `migrations/002_add_email_notifications.sql` - Database migration

### Modified Files (6)
1. `aibc_auth/app/core/config.py` - Add email settings
2. `aibc_auth/app/api/v1/resources.py` - Add approval/rejection email triggers
3. `aibc_auth/app/api/v1/progress.py` - Add submission email trigger
4. `admin_dashboard/app.py` - Add email triggers for Flask routes
5. `aibc_auth/requirements.txt` - Add 4 dependencies
6. `aibc_auth/.env` - Add email configuration variables

### Dependencies Added (4)
1. `aiosmtplib` - Async SMTP client
2. `jinja2` - Template engine
3. `premailer` - CSS inlining for emails
4. `beautifulsoup4` - HTML parsing

---

## Implementation Benefits

✅ **Student Experience**
- Instant feedback on submissions
- Clear next steps when revisions needed
- Encouragement on approvals
- Reduced uncertainty during review process

✅ **Admin Efficiency**
- Immediate awareness of pending reviews
- Reduced need to manually check dashboard
- Student context in notification (progress, history)
- Faster review turnaround

✅ **Production-Grade**
- Async/non-blocking email delivery
- Retry logic for reliability
- Audit logging for compliance
- Rate limiting to prevent abuse
- Template-based for easy updates
- HTML + plain text for compatibility

✅ **Low-Code Additive**
- No breaking changes to existing code
- Feature flags for gradual rollout
- Existing workflow preserved
- Emails are non-critical (failures don't block operations)
- Easy to disable if issues arise

✅ **Scalable**
- Works with Gmail (development) or SendGrid/SES (production)
- Connection pooling for efficiency
- Queue-based for high volume
- Configurable rate limits

---

## Deployment Checklist

**Before Deployment:**
1. Create app-specific password for Gmail or setup SendGrid/SES account
2. Add all environment variables to `.env` and `.env.production`
3. Run database migration `002_add_email_notifications.sql`
4. Install new Python dependencies
5. Create email templates directory and files
6. Test email delivery in development environment
7. Verify email templates render correctly on multiple clients (Gmail, Outlook, mobile)
8. Set up SPF/DKIM/DMARC records for production domain
9. Configure feature flags (`EMAIL_NOTIFICATIONS_ENABLED=true`)

**After Deployment:**
1. Monitor email logs table for delivery issues
2. Check SMTP server logs for authentication problems
3. Verify admin notifications arrive at configured email addresses
4. Test student notification flow end-to-end
5. Monitor email delivery rates and bounce statistics
6. Set up alerts for email failures exceeding threshold

---

## Email Content Best Practices

1. **Subject Lines**
   - Clear and specific: "✅ Module Approved: AI Agent Fundamentals"
   - Include action if needed: "📝 Revision Requested: Image Classification Project"
   - Keep under 50 characters for mobile

2. **Body Content**
   - Personalize with student name
   - State purpose in first sentence
   - Use clear formatting (headings, lists, buttons)
   - Include actionable next steps
   - Add relevant links (dashboard, module, help)
   - Keep tone encouraging and supportive

3. **Design**
   - Mobile-responsive (600px max width)
   - Use web-safe fonts
   - Inline CSS for compatibility
   - Test on major email clients (Gmail, Outlook, Apple Mail)
   - Include plain text fallback

4. **Compliance**
   - Include organization name and contact info
   - Add unsubscribe link (future enhancement)
   - Don't send marketing without consent
   - Respect user email preferences

---

**End of Implementation Plan**
