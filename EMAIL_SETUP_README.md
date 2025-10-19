# Email Notification System - Setup & Configuration

## Overview

The AI Bootcamp platform now includes a production-grade email notification system that automatically sends emails to:
- **Students**: When modules are approved or need revision
- **Admins**: When new modules are submitted for review

## Quick Start

### 1. Configure SMTP Credentials

Edit your `.env` or `.env.production` file and add your SMTP credentials:

```bash
# Email Notification Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=noreply@aiclub-bootcamp.com
SMTP_FROM_NAME=AI Bootcamp
SMTP_USE_TLS=true

# Admin notification recipients (comma-separated)
ADMIN_EMAILS=romanslack1@gmail.com,admin2@example.com

# Email feature flags (set to false to disable)
EMAIL_NOTIFICATIONS_ENABLED=true
SEND_STUDENT_NOTIFICATIONS=true
SEND_ADMIN_NOTIFICATIONS=true
```

### 2. Setup Gmail App Password (Recommended for Development)

If using Gmail SMTP:

1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Go to "App passwords" (appears after 2FA enabled)
4. Generate new app password for "Mail"
5. Copy the 16-character password
6. Use this password as `SMTP_PASSWORD` in your `.env` file

**Important**: Never use your actual Gmail password - use app-specific passwords only.

### 3. Run Database Migration

Apply the email notification database schema:

```bash
# Connect to your database
psql -h localhost -U aibc_admin -d aibc_db

# Run migration
\i migrations/002_add_email_notifications.sql
```

Or if using Docker:
```bash
docker exec -i aibc-postgres psql -U aibc_admin -d aibc_db < migrations/002_add_email_notifications.sql
```

### 4. Install Python Dependencies

```bash
# For FastAPI backend
cd aibc_auth
pip install -r requirements.txt

# For admin dashboard
cd ../admin_dashboard
pip install -r requirements.txt
```

### 5. Test Email Configuration

You can test email sending by submitting a module for review or by checking the logs when emails are triggered.

## Email Triggers

### Student Notifications

#### 1. Module Approved ✅
**When**: Admin approves the last required resource → module auto-approved
**Email**: `module_approved.html`
**Subject**: "✅ Module Approved: [Module Title]"
**Content**:
- Congratulations message
- Module and pathway details
- Approval date and reviewer name
- Next module recommendation
- Link to dashboard

#### 2. Module Rejected 📝
**When**: Admin rejects a resource submission
**Email**: `module_rejected.html`
**Subject**: "📝 Revision Requested: [Resource Title]"
**Content**:
- Instructor feedback
- Steps to revise and resubmit
- Link to module

### Admin Notifications

#### 3. Module Submitted 📋
**When**: Student clicks "Submit for Review"
**Email**: `module_submitted.html`
**Subject**: "📋 New Module Submission: [Module Title] by [Student Name]"
**Content**:
- Student name and email
- Pathway and module details
- List of resources to review
- Student progress summary
- Link to admin dashboard

**Recipients**: All emails in `ADMIN_EMAILS` environment variable

## Email Templates

Located in: `aibc_auth/app/templates/emails/`

Each email has both HTML and plain text versions:
- `module_approved.html` / `module_approved.txt`
- `module_rejected.html` / `module_rejected.txt`
- `module_submitted.html` / `module_submitted.txt`
- `base.html` (shared template)

Templates use Jinja2 syntax and can be customized with your branding.

## Production SMTP Providers

### Option 1: Gmail (Development/Low Volume)
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-specific-password
```
- **Limit**: 500 emails/day
- **Cost**: Free
- **Setup**: Requires app password (see above)

### Option 2: SendGrid (Recommended for Production)
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```
- **Limit**: 100/day free, 40k/month paid
- **Cost**: Free tier, $15+/month for paid
- **Signup**: https://sendgrid.com/
- **Benefits**: Better deliverability, analytics, templates

### Option 3: Amazon SES (Cost-Effective for High Volume)
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```
- **Limit**: 62k/month free with AWS free tier
- **Cost**: $0.10 per 1,000 emails
- **Setup**: https://aws.amazon.com/ses/
- **Benefits**: Scalable, cheap, reliable

### Option 4: Mailgun
```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=your-mailgun-username
SMTP_PASSWORD=your-mailgun-password
```
- **Limit**: 5k/month free
- **Cost**: $35/month for 50k emails
- **Signup**: https://www.mailgun.com/

## Email Logging & Monitoring

All sent emails are logged in the `email_logs` table:

```sql
SELECT
    recipient_email,
    email_type,
    subject,
    status,
    created_at,
    sent_at,
    error_message
FROM email_logs
ORDER BY created_at DESC
LIMIT 50;
```

### Email Status Values:
- `pending`: Queued for sending
- `sent`: Successfully delivered
- `failed`: Delivery failed (check `error_message`)
- `bounced`: Email bounced (invalid address)

### Query Failed Emails:
```sql
SELECT * FROM email_logs
WHERE status = 'failed'
ORDER BY created_at DESC;
```

## Feature Flags

Control email behavior with environment variables:

```bash
# Master switch - disables ALL emails
EMAIL_NOTIFICATIONS_ENABLED=false

# Disable only student notifications
SEND_STUDENT_NOTIFICATIONS=false

# Disable only admin notifications
SEND_ADMIN_NOTIFICATIONS=false
```

## Troubleshooting

### Emails Not Sending

1. **Check SMTP credentials**:
   ```bash
   # Verify credentials are set
   echo $SMTP_USERNAME
   echo $SMTP_PASSWORD
   ```

2. **Check logs**:
   ```bash
   # FastAPI logs
   docker logs aibc-auth-service | grep -i email

   # Admin dashboard logs
   docker logs admin-dashboard | grep -i email
   ```

3. **Test SMTP connection**:
   ```python
   import smtplib

   smtp = smtplib.SMTP('smtp.gmail.com', 587)
   smtp.starttls()
   smtp.login('your-email@gmail.com', 'your-app-password')
   smtp.quit()
   print("SMTP connection successful!")
   ```

4. **Check email_logs table**:
   ```sql
   SELECT * FROM email_logs
   WHERE status = 'failed'
   ORDER BY created_at DESC
   LIMIT 10;
   ```

### Gmail "Less Secure Apps" Error

If using Gmail and getting authentication errors:
1. Don't use "less secure apps" - this is deprecated
2. **Use app-specific passwords** (see Setup section above)
3. Ensure 2FA is enabled on your Google account

### Emails Going to Spam

1. **Add SPF record** to your domain DNS:
   ```
   v=spf1 include:_spf.google.com ~all
   ```

2. **Add DKIM** (if using SendGrid/SES):
   - Follow provider's instructions to add DKIM records

3. **Use professional from address**:
   ```bash
   SMTP_FROM_EMAIL=noreply@yourdomain.com
   ```

4. **Warm up IP** (for high-volume sending):
   - Start with low volume
   - Gradually increase over 2-4 weeks

## Security Best Practices

1. **Never commit credentials**:
   - Use `.env` files (already in `.gitignore`)
   - Use environment variables or secret managers

2. **Use app-specific passwords**:
   - Never use your main email password
   - Generate separate passwords for each app

3. **Rotate credentials regularly**:
   - Change SMTP passwords every 90 days
   - Revoke unused app passwords

4. **Monitor for abuse**:
   - Check `email_logs` for unusual patterns
   - Set up alerts for high email volume

5. **Rate limiting**:
   ```bash
   EMAIL_RATE_LIMIT_PER_HOUR=50
   ```

## Customization

### Customize Email Templates

Edit files in `aibc_auth/app/templates/emails/`:

```html
<!-- module_approved.html -->
{% extends "base.html" %}
{% block content %}
<h2>Your custom message</h2>
<p>Hi {{ user_name }}, ...</p>
{% endblock %}
```

### Customize Email Branding

Edit `base.html`:
```html
<div class="header">
    <h1>🚀 Your Brand Name</h1>
</div>
```

### Add New Email Types

1. Create template: `emails/new_template.html`
2. Add method to `EmailService` class
3. Call method from appropriate trigger point

## Performance & Scaling

### Current Capacity
- Async/non-blocking email delivery
- Retry logic with exponential backoff
- Rate limiting: 50 emails/hour (configurable)
- Connection pooling for efficiency

### High-Volume Optimization
If sending >1000 emails/day:

1. **Use SendGrid or AWS SES** (not Gmail)
2. **Enable connection pooling**:
   ```python
   # Already implemented in EmailService
   ```
3. **Queue emails** for batch processing:
   ```bash
   # Use background workers (Celery/RQ) for very high volume
   ```
4. **Monitor delivery rates**:
   ```sql
   SELECT
       DATE(created_at) as date,
       COUNT(*) as total,
       COUNT(*) FILTER (WHERE status='sent') as sent,
       COUNT(*) FILTER (WHERE status='failed') as failed
   FROM email_logs
   GROUP BY DATE(created_at)
   ORDER BY date DESC;
   ```

## Support

### Common Issues

**Q: Emails are slow to send**
A: Email sending is async and non-blocking. Check SMTP server response times.

**Q: Can I use a custom domain?**
A: Yes, configure `SMTP_FROM_EMAIL=noreply@yourdomain.com` and add SPF/DKIM records.

**Q: How do I add more admin emails?**
A: Update `ADMIN_EMAILS` with comma-separated list: `admin1@x.com,admin2@x.com`

**Q: Can I disable emails temporarily?**
A: Yes, set `EMAIL_NOTIFICATIONS_ENABLED=false` in `.env`

### Get Help

- Check logs: `docker logs aibc-auth-service | grep -i email`
- Review `email_logs` table for failures
- Test SMTP connection independently
- Verify environment variables are loaded

## Architecture

```
User Action (Submit/Approve)
        ↓
FastAPI/Flask Handler
        ↓
Email Service (async)
        ↓
Create email_logs entry (status=pending)
        ↓
Render Jinja2 template (HTML + Text)
        ↓
Send via SMTP (with retry logic)
        ↓
Update email_logs (status=sent/failed)
```

**Non-blocking**: Email failures never block user requests.
**Retry Logic**: 3 attempts with exponential backoff.
**Audit Trail**: All emails logged in database.

---

## Summary

✅ **Production-ready** email notification system
✅ **Fully automated** - no manual intervention needed
✅ **Secure** - uses TLS encryption and app passwords
✅ **Reliable** - retry logic and error handling
✅ **Auditable** - complete email logs in database
✅ **Flexible** - easily customize templates and triggers
✅ **Scalable** - async delivery, works with major SMTP providers

Configure your SMTP credentials, run the migration, and you're ready to go!
