#!/usr/bin/env python3
"""
AI Bootcamp Admin Dashboard - Submission Grading Tool
Simple Flask app for instructors to review and grade student submissions
"""
import os
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment from parent directory
load_dotenv('/home/roman/ai_bootcamp_backend/aibc_auth/.env')

app = Flask(__name__)
app.secret_key = 'admin-dashboard-secret-key'

# Database connection using .env
DB_URL = os.getenv('DATABASE_URL', 'postgresql://aibc_admin:AIbc2024SecurePass@localhost:5432/aibc_db')
# Replace 'postgres' with 'localhost' for local connection
DB_URL = DB_URL.replace('postgres:', 'localhost:')

def get_db():
    """Get database connection"""
    return psycopg2.connect(DB_URL)

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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { font-size: 28px; font-weight: 700; }
        .stats {
            display: flex;
            gap: 20px;
            padding: 20px 40px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }
        .stat-card {
            background: white;
            padding: 15px 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            flex: 1;
        }
        .stat-number { font-size: 32px; font-weight: 700; color: #667eea; }
        .stat-label { font-size: 13px; color: #6c757d; margin-top: 5px; }
        .filters {
            padding: 20px 40px;
            background: #fff;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        select, input {
            padding: 10px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
        }
        select:hover, input:hover { border-color: #667eea; }
        select:focus, input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        .submissions {
            padding: 20px 40px;
            max-height: 600px;
            overflow-y: auto;
        }
        .submission-card {
            background: #fff;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }
        .submission-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102,126,234,0.15);
        }
        .submission-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .student-info h3 { font-size: 18px; color: #212529; margin-bottom: 5px; }
        .student-info p { font-size: 14px; color: #6c757d; }
        .resource-title { font-size: 15px; color: #495057; font-weight: 600; margin-top: 5px; }
        .submission-meta {
            display: flex;
            gap: 20px;
            margin: 15px 0;
            font-size: 13px;
            color: #6c757d;
        }
        .meta-item { display: flex; align-items: center; gap: 5px; }
        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-pending { background: #fff3cd; color: #856404; }
        .badge-uploaded { background: #d1ecf1; color: #0c5460; }
        .badge-approved { background: #d4edda; color: #155724; }
        .badge-rejected { background: #f8d7da; color: #721c24; }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .review-form {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
        .review-form.active { display: block; }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            min-height: 80px;
            outline: none;
        }
        textarea:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-size: 13px; font-weight: 600; color: #495057; margin-bottom: 5px; }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }
        .empty-state h3 { font-size: 20px; margin-bottom: 10px; }
        .file-info {
            background: #e9ecef;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 13px;
        }
        .waiting-time {
            font-size: 13px;
            color: #dc3545;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 Submission Grading Dashboard</h1>
            <div style="font-size: 14px; opacity: 0.9;">AI Bootcamp Admin</div>
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
                <div class="stat-number">{{ stats.avg_wait_hours|round(1) }}h</div>
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
                    <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 8px; font-size: 13px;">
                        <strong>Previous Feedback:</strong> {{ sub.review_comments }}
                    </div>
                    {% endif %}

                    <div class="actions">
                        <a href="{{ sub.gcs_url }}" target="_blank" class="btn btn-primary">Download File</a>
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
