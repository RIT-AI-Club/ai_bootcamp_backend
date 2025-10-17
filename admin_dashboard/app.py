#!/usr/bin/env python3
"""
AI Bootcamp Admin Dashboard - Submission Grading Tool
Simple Flask app for instructors to review and grade student submissions
"""
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account

# Load environment from parent directory
load_dotenv('/home/roman/ai_bootcamp_backend/aibc_auth/.env')

app = Flask(__name__)
app.secret_key = 'admin-dashboard-secret-key'

# Database connection using .env
DB_URL = os.getenv('DATABASE_URL', 'postgresql://aibc_admin:AIbc2024SecurePass@localhost:5432/aibc_db')
# Replace 'postgres' with 'localhost' for local connection
DB_URL = DB_URL.replace('postgres:', 'localhost:')

# Google Cloud Storage setup
GCS_BUCKET = os.getenv('GCS_BUCKET_NAME', 'aibc-submissions')
GCS_PROJECT = os.getenv('GCS_PROJECT_ID', 'ai-bootcamp-475320')

def get_gcs_credentials_path():
    """
    Get GCS credentials path with intelligent fallback
    Matches pattern from aibc_auth/app/core/gcs.py
    """
    # First, try environment variable (for Cloud Run: /app/gcs-key.json)
    env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

    if env_path and os.path.exists(env_path):
        return env_path

    # Second, try relative path from admin_dashboard directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    relative_path = os.path.join(script_dir, '..', 'aibc_auth', 'gcs-key.json')

    if os.path.exists(relative_path):
        return os.path.abspath(relative_path)

    # Third, try current directory (for Docker if mounted)
    current_dir_path = os.path.join(os.getcwd(), 'gcs-key.json')
    if os.path.exists(current_dir_path):
        return current_dir_path

    return None

def get_gcs_client():
    """
    Get GCS client with credential fallback
    Matches pattern from aibc_auth/app/core/gcs.py
    """
    try:
        credentials_path = get_gcs_credentials_path()

        if credentials_path:
            # Use service account credentials (local development)
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            return storage.Client(credentials=credentials, project=GCS_PROJECT)
        else:
            # Use default credentials (Cloud Run with workload identity)
            return storage.Client(project=GCS_PROJECT)

    except Exception as e:
        print(f"Warning: GCS client initialization failed: {e}")
        return None

def get_db():
    """Get database connection"""
    return psycopg2.connect(DB_URL)

def generate_signed_url(gcs_path):
    """Generate signed URL for GCS file download"""
    try:
        # Extract blob path from gs:// URL
        if gcs_path.startswith('gs://'):
            blob_path = gcs_path.replace(f'gs://{GCS_BUCKET}/', '')
        else:
            blob_path = gcs_path

        client = get_gcs_client()
        if not client:
            return None

        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)

        # Generate signed URL valid for 1 hour
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )

        return signed_url
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        return None

# =============================================================================
# HTML TEMPLATES (embedded for single-file simplicity)
# =============================================================================

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Submission Grading</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            background: #0a0a0a;
            min-height: 100vh;
            padding: 20px;
            color: #00ff41;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: #0f0f0f;
            border-radius: 4px;
            border: 1px solid #00ff41;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.1);
            overflow: hidden;
        }
        header {
            background: #000;
            color: #00ff41;
            padding: 30px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #00ff41;
        }
        h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }
        h1::before { content: '> '; color: #00ff41; }
        .stats {
            display: flex;
            gap: 20px;
            padding: 20px 40px;
            background: #000;
            border-bottom: 1px solid #1a1a1a;
        }
        .stat-card {
            background: #0a0a0a;
            padding: 15px 25px;
            border-radius: 4px;
            border: 1px solid #1a1a1a;
            flex: 1;
            transition: all 0.2s;
        }
        .stat-card:hover {
            border-color: #00ff41;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        }
        .stat-number {
            font-size: 32px;
            font-weight: 700;
            color: #00ff41;
            font-variant-numeric: tabular-nums;
        }
        .stat-label {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .filters {
            padding: 20px 40px;
            background: #000;
            border-bottom: 1px solid #1a1a1a;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        select, input {
            padding: 10px 15px;
            border: 1px solid #1a1a1a;
            border-radius: 2px;
            font-size: 13px;
            background: #0a0a0a;
            color: #00ff41;
            font-family: 'JetBrains Mono', monospace;
            outline: none;
            transition: all 0.2s;
        }
        select:hover, input:hover {
            border-color: #00ff41;
            box-shadow: 0 0 5px rgba(0, 255, 65, 0.3);
        }
        select:focus, input:focus {
            border-color: #00ff41;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }
        .submissions {
            padding: 20px 40px;
            max-height: 600px;
            overflow-y: auto;
            background: #000;
        }
        .submissions::-webkit-scrollbar { width: 8px; }
        .submissions::-webkit-scrollbar-track { background: #0a0a0a; }
        .submissions::-webkit-scrollbar-thumb {
            background: #1a1a1a;
            border-radius: 4px;
        }
        .submissions::-webkit-scrollbar-thumb:hover { background: #00ff41; }
        .submission-card {
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 4px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }
        .submission-card:hover {
            border-color: #00ff41;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.2);
        }
        .submission-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .student-info h3 {
            font-size: 16px;
            color: #00ff41;
            margin-bottom: 5px;
            letter-spacing: 1px;
        }
        .student-info h3::before { content: '// '; color: #666; }
        .student-info p {
            font-size: 12px;
            color: #999;
        }
        .resource-title {
            font-size: 13px;
            color: #aaa;
            font-weight: 500;
            margin-top: 5px;
        }
        .submission-meta {
            display: flex;
            gap: 20px;
            margin: 15px 0;
            font-size: 11px;
            color: #666;
        }
        .meta-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .meta-item::before { content: '['; color: #00ff41; }
        .meta-item::after { content: ']'; color: #00ff41; }
        .badge {
            padding: 4px 10px;
            border-radius: 2px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid;
        }
        .badge-pending { background: #1a1a00; color: #ffff00; border-color: #ffff00; }
        .badge-uploaded { background: #001a1a; color: #00ffff; border-color: #00ffff; }
        .badge-approved { background: #001a00; color: #00ff41; border-color: #00ff41; }
        .badge-rejected { background: #1a0000; color: #ff0000; border-color: #ff0000; }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 8px 16px;
            border: 1px solid;
            border-radius: 2px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn:hover {
            box-shadow: 0 0 10px;
            transform: translateY(-1px);
        }
        .btn-primary {
            background: #001a1a;
            color: #00ffff;
            border-color: #00ffff;
        }
        .btn-primary:hover { box-shadow: 0 0 10px rgba(0, 255, 255, 0.5); }
        .btn-success {
            background: #001a00;
            color: #00ff41;
            border-color: #00ff41;
        }
        .btn-success:hover { box-shadow: 0 0 10px rgba(0, 255, 65, 0.5); }
        .btn-danger {
            background: #1a0000;
            color: #ff0000;
            border-color: #ff0000;
        }
        .btn-danger:hover { box-shadow: 0 0 10px rgba(255, 0, 0, 0.5); }
        .btn-secondary {
            background: #0a0a0a;
            color: #666;
            border-color: #333;
        }
        .btn-secondary:hover {
            color: #00ff41;
            border-color: #00ff41;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }
        .review-form {
            margin-top: 15px;
            padding: 15px;
            background: #000;
            border: 1px solid #1a1a1a;
            border-radius: 4px;
            display: none;
        }
        .review-form.active { display: block; }
        textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #1a1a1a;
            border-radius: 2px;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            background: #0a0a0a;
            color: #00ff41;
            resize: vertical;
            min-height: 80px;
            outline: none;
        }
        textarea:focus {
            border-color: #00ff41;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }
        .form-group { margin-bottom: 15px; }
        label {
            display: block;
            font-size: 11px;
            font-weight: 600;
            color: #00ff41;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        label::before { content: '> '; }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h3 {
            font-size: 18px;
            margin-bottom: 10px;
            color: #00ff41;
        }
        .file-info {
            background: #000;
            border: 1px solid #1a1a1a;
            padding: 10px 15px;
            border-radius: 2px;
            margin: 10px 0;
            font-size: 11px;
            color: #888;
        }
        .file-info strong {
            color: #00ff41;
        }
        .waiting-time {
            font-size: 11px;
            color: #ff0000;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SUBMISSION_GRADING_SYS</h1>
            <div style="font-size: 11px; color: #666; letter-spacing: 2px;">AIBC://ADMIN_TERMINAL</div>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_pending }}</div>
                <div class="stat-label">Pending Review</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_uploaded }}</div>
                <div class="stat-label">Uploaded Today</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ (stats.avg_wait_hours|round(1)) if stats.avg_wait_hours else 0 }}h</div>
                <div class="stat-label">Avg Wait Time</div>
            </div>
        </div>

        <div class="filters">
            <select id="pathwayFilter" onchange="filterSubmissions()">
                <option value="">All Pathways</option>
                {% for pathway in pathways %}
                <option value="{{ pathway.id }}">{{ pathway.title }}</option>
                {% endfor %}
            </select>
            <select id="statusFilter" onchange="filterSubmissions()">
                <option value="uploaded">Pending Review</option>
                <option value="">All Statuses</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
            </select>
            <input type="text" id="searchInput" placeholder="Search student name..." onkeyup="filterSubmissions()">
        </div>

        <div class="submissions">
            {% if submissions %}
                {% for sub in submissions %}
                <div class="submission-card" data-pathway="{{ sub.pathway_id }}" data-status="{{ sub.submission_status }}" data-student="{{ sub.user_name|lower }}">
                    <div class="submission-header">
                        <div class="student-info">
                            <h3>{{ sub.user_name }}</h3>
                            <p>{{ sub.user_email }}</p>
                            <div class="resource-title">{{ sub.resource_title }}</div>
                        </div>
                        <span class="badge badge-{{ sub.submission_status }}">{{ sub.submission_status }}</span>
                    </div>

                    <div class="submission-meta">
                        <div class="meta-item">
                            <span>📁</span>
                            <span>{{ sub.file_name }}</span>
                        </div>
                        <div class="meta-item">
                            <span>📦</span>
                            <span>{{ (sub.file_size_bytes / 1024 / 1024)|round(2) }} MB</span>
                        </div>
                        <div class="meta-item">
                            <span>📅</span>
                            <span>{{ sub.created_at.strftime('%Y-%m-%d %H:%M') }}</span>
                        </div>
                        {% if sub.hours_waiting %}
                        <div class="meta-item waiting-time">
                            <span>⏱️</span>
                            <span>{{ sub.hours_waiting|round(1) }}h waiting</span>
                        </div>
                        {% endif %}
                    </div>

                    <div class="file-info">
                        <strong>Pathway:</strong> {{ sub.pathway_title }} |
                        <strong>Module:</strong> {{ sub.module_title }}
                    </div>

                    {% if sub.review_comments %}
                    <div style="margin-top: 10px; padding: 12px; background: #1a1a00; border: 1px solid #ffff00; border-radius: 4px; font-size: 12px; color: #ffff00;">
                        <strong style="color: #ffff00;">Previous Feedback:</strong> {{ sub.review_comments }}
                    </div>
                    {% endif %}

                    <div class="actions">
                        <button class="btn btn-primary" onclick="downloadFile('{{ sub.id }}', '{{ sub.gcs_path }}')">Download File</button>
                        {% if sub.submission_status == 'uploaded' %}
                        <button class="btn btn-secondary" onclick="toggleReviewForm('{{ sub.id }}')">Review</button>
                        {% endif %}
                    </div>

                    <div id="review-{{ sub.id }}" class="review-form">
                        <form onsubmit="submitReview(event, '{{ sub.id }}')">
                            <div class="form-group">
                                <label>Grade</label>
                                <select name="grade" required>
                                    <option value="">Select grade...</option>
                                    <option value="pass">✓ Pass</option>
                                    <option value="fail">✗ Fail</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Feedback (optional)</label>
                                <textarea name="comments" placeholder="Provide feedback to the student..."></textarea>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <button type="submit" name="status" value="approved" class="btn btn-success">Approve</button>
                                <button type="submit" name="status" value="rejected" class="btn btn-danger">Reject & Request Revision</button>
                                <button type="button" class="btn btn-secondary" onclick="toggleReviewForm('{{ sub.id }}')">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <h3>🎉 All caught up!</h3>
                    <p>No pending submissions to review</p>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        function downloadFile(submissionId, gcsPath) {
            // Get signed URL from backend
            fetch('/api/download/' + submissionId)
                .then(response => response.json())
                .then(data => {
                    if (data.signed_url) {
                        window.open(data.signed_url, '_blank');
                    } else {
                        alert('Failed to generate download link: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    alert('Failed to download file: ' + error);
                });
        }

        function toggleReviewForm(id) {
            const form = document.getElementById('review-' + id);
            form.classList.toggle('active');
        }

        function submitReview(event, submissionId) {
            event.preventDefault();
            const form = event.target;
            const formData = new FormData(form);
            const button = event.submitter;

            const data = {
                submission_status: button.value,
                grade: formData.get('grade'),
                review_comments: formData.get('comments')
            };

            fetch('/api/review/' + submissionId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Failed to submit review: ' + error);
            });
        }

        function filterSubmissions() {
            const pathway = document.getElementById('pathwayFilter').value.toLowerCase();
            const status = document.getElementById('statusFilter').value.toLowerCase();
            const search = document.getElementById('searchInput').value.toLowerCase();

            document.querySelectorAll('.submission-card').forEach(card => {
                const matchPathway = !pathway || card.dataset.pathway.toLowerCase().includes(pathway);
                const matchStatus = !status || card.dataset.status.toLowerCase() === status;
                const matchSearch = !search || card.dataset.student.includes(search);

                card.style.display = (matchPathway && matchStatus && matchSearch) ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all submissions with related data
    cur.execute("""
        SELECT
            rs.id,
            rs.user_id,
            u.email as user_email,
            u.full_name as user_name,
            rs.resource_id,
            r.title as resource_title,
            r.type as resource_type,
            r.pathway_id,
            r.module_id,
            p.title as pathway_title,
            m.title as module_title,
            rs.file_name,
            rs.file_size_bytes,
            rs.file_type,
            rs.gcs_url,
            rs.gcs_path,
            rs.submission_status,
            rs.grade,
            rs.review_comments,
            rs.created_at,
            rs.reviewed_at,
            EXTRACT(EPOCH FROM (NOW() - rs.created_at))/3600 as hours_waiting
        FROM resource_submissions rs
        JOIN users u ON rs.user_id = u.id
        JOIN resources r ON rs.resource_id = r.id
        JOIN pathways p ON r.pathway_id = p.id
        JOIN modules m ON r.module_id = m.id
        WHERE rs.deleted_at IS NULL
        ORDER BY
            CASE
                WHEN rs.submission_status = 'uploaded' THEN 0
                WHEN rs.submission_status = 'rejected' THEN 1
                ELSE 2
            END,
            rs.created_at ASC
        LIMIT 100
    """)
    submissions = cur.fetchall()

    # Get stats
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE submission_status = 'uploaded') as total_pending,
            COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as total_uploaded,
            AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/3600)
                FILTER (WHERE submission_status = 'uploaded') as avg_wait_hours
        FROM resource_submissions
        WHERE deleted_at IS NULL
    """)
    stats = cur.fetchone()

    # Get pathways for filter
    cur.execute("SELECT id, title FROM pathways ORDER BY title")
    pathways = cur.fetchall()

    cur.close()
    conn.close()

    return render_template_string(
        INDEX_TEMPLATE,
        submissions=submissions,
        stats=stats or {'total_pending': 0, 'total_uploaded': 0, 'avg_wait_hours': 0},
        pathways=pathways
    )

@app.route('/api/download/<submission_id>')
def download_file(submission_id):
    """Generate signed URL for file download"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get submission's GCS path
        cur.execute("""
            SELECT gcs_path, gcs_url, file_name
            FROM resource_submissions
            WHERE id = %s
        """, (submission_id,))

        submission = cur.fetchone()
        cur.close()
        conn.close()

        if not submission:
            return jsonify({'error': 'Submission not found'}), 404

        # Generate signed URL
        signed_url = generate_signed_url(submission['gcs_path'] or submission['gcs_url'])

        if signed_url:
            return jsonify({'signed_url': signed_url, 'file_name': submission['file_name']})
        else:
            return jsonify({'error': 'Failed to generate download link'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/review/<submission_id>', methods=['POST'])
def review_submission(submission_id):
    """Review and grade a submission"""
    data = request.json
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE resource_submissions
            SET submission_status = %s,
                grade = %s,
                review_comments = %s,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (
            data['submission_status'],
            data.get('grade'),
            data.get('review_comments'),
            submission_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Review submitted successfully'})

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI Bootcamp Admin Dashboard")
    print("=" * 60)
    print(f"📊 Dashboard URL: http://localhost:5000")
    print(f"🔗 Database: {DB_URL.split('@')[1].split('/')[0]}")
    print("=" * 60)
    print("\n✅ Starting server...\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
