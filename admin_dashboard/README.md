# AI Bootcamp Admin Dashboard

Simple submission grading tool for instructors.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
python app.py

# 3. Open browser
http://localhost:5000
```

## Features

✅ **View All Submissions** - See pending, approved, and rejected submissions
✅ **Filter & Search** - Filter by pathway, status, or search by student name
✅ **Download Files** - Direct download links from Google Cloud Storage
✅ **Grade Submissions** - Approve or reject with feedback
✅ **Real-time Stats** - Pending count, upload stats, average wait time
✅ **No Docker** - Single Python file, connects directly to PostgreSQL

## How It Works

1. **Database Connection** - Reads from same PostgreSQL DB as main backend
2. **Reviews Submissions** - Shows all `resource_submissions` needing review
3. **Grading** - Instructors can approve (pass/fail) or reject for revision
4. **Updates Status** - Changes `submission_status` and adds feedback

## Database Access

Uses environment variables from `/home/roman/ai_bootcamp_backend/aibc_auth/.env`:
- `DATABASE_URL` - PostgreSQL connection string
- Automatically replaces `postgres:` with `localhost:` for local access

## API Endpoints

- `GET /` - Main dashboard UI
- `POST /api/review/<submission_id>` - Submit grade/review

## Security Note

This is an internal tool. For production:
- Add authentication (basic auth, API key, or SSO)
- Add role-based access control
- Add HTTPS/SSL
- Add rate limiting

## Port

Runs on `http://localhost:5000` by default.
