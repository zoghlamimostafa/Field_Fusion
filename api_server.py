"""
Flask API Server for Football AI Analysis System
Provides REST endpoints for video analysis, real-time streaming, and analytics
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# Import project modules
from complete_pipeline import main as run_complete_pipeline
from analytics_exporter import AnalyticsExporter
from realtime_stream_processor import RealtimeStreamProcessor
from rate_limiter import rate_limit, get_rate_limit_info

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Allowed video extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}

# In-memory user database (replace with real database in production)
users_db = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'role': 'admin',
        'api_key': 'demo-api-key-123'
    }
}

# Job tracking (replace with Redis/database in production)
jobs_db = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def token_required(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        try:
            # Decode token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['username']

            # Verify user exists
            if current_user not in users_db:
                return jsonify({'error': 'Invalid token'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.route('/api/auth/register', methods=['POST'])
@rate_limit(limit_type='auth', cost=1)
def register():
    """Register a new user"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    username = data['username']

    if username in users_db:
        return jsonify({'error': 'User already exists'}), 400

    # Create new user
    users_db[username] = {
        'password': generate_password_hash(data['password']),
        'role': data.get('role', 'user'),
        'api_key': str(uuid.uuid4())
    }

    return jsonify({
        'message': 'User registered successfully',
        'username': username,
        'api_key': users_db[username]['api_key']
    }), 201


@app.route('/api/auth/login', methods=['POST'])
@rate_limit(limit_type='auth', cost=1)
def login():
    """Login and receive JWT token"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    username = data['username']

    if username not in users_db:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Verify password
    if not check_password_hash(users_db[username]['password'], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate JWT token (expires in 24 hours)
    token = jwt.encode({
        'username': username,
        'role': users_db[username]['role'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'token': token,
        'username': username,
        'role': users_db[username]['role'],
        'expires_in': 86400  # 24 hours in seconds
    }), 200


# =============================================================================
# VIDEO ANALYSIS ENDPOINTS
# =============================================================================

@app.route('/api/analyze/upload', methods=['POST'])
@token_required
@rate_limit(limit_type='upload', cost=1)
def upload_video(current_user):
    """Upload a video for analysis"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Save file
    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(upload_path)

    # Create job record
    jobs_db[job_id] = {
        'id': job_id,
        'user': current_user,
        'filename': filename,
        'upload_path': upload_path,
        'status': 'uploaded',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    return jsonify({
        'message': 'Video uploaded successfully',
        'job_id': job_id,
        'filename': filename
    }), 201


@app.route('/api/analyze/start/<job_id>', methods=['POST'])
@token_required
@rate_limit(limit_type='analysis', cost=1)
def start_analysis(current_user, job_id):
    """Start analysis on uploaded video"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['user'] != current_user and users_db[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if job['status'] not in ['uploaded', 'failed']:
        return jsonify({'error': f'Job is already {job["status"]}'}), 400

    # Get analysis options from request
    data = request.get_json() or {}
    analysis_level = data.get('level', 3)  # Default to level 3

    # Update job status
    job['status'] = 'processing'
    job['updated_at'] = datetime.utcnow().isoformat()
    job['analysis_level'] = analysis_level

    try:
        # Run analysis (this should be async in production with Celery/RQ)
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        os.makedirs(output_dir, exist_ok=True)

        # Note: In production, use a task queue (Celery, RQ, etc.)
        # For now, we'll run synchronously (this will block the request)
        run_complete_pipeline(
            video_path=job['upload_path'],
            output_dir=output_dir,
            level=analysis_level
        )

        # Update job with results
        job['status'] = 'completed'
        job['updated_at'] = datetime.utcnow().isoformat()
        job['output_dir'] = output_dir

        # Find output files
        job['results'] = {
            'video': find_output_video(output_dir),
            'reports': find_reports(output_dir),
            'heatmaps': find_heatmaps(output_dir)
        }

        return jsonify({
            'message': 'Analysis completed successfully',
            'job_id': job_id,
            'results': job['results']
        }), 200

    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        job['updated_at'] = datetime.utcnow().isoformat()

        return jsonify({
            'error': 'Analysis failed',
            'message': str(e)
        }), 500


@app.route('/api/analyze/status/<job_id>', methods=['GET'])
@token_required
def get_job_status(current_user, job_id):
    """Get analysis job status"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['user'] != current_user and users_db[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(job), 200


@app.route('/api/analyze/results/<job_id>', methods=['GET'])
@token_required
def get_results(current_user, job_id):
    """Get analysis results"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['user'] != current_user and users_db[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    return jsonify({
        'job_id': job_id,
        'results': job.get('results', {}),
        'completed_at': job['updated_at']
    }), 200


@app.route('/api/analyze/download/<job_id>/<file_type>', methods=['GET'])
@token_required
@rate_limit(limit_type='download', cost=1)
def download_result(current_user, job_id, file_type):
    """Download result files (video, report, heatmap)"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['user'] != current_user and users_db[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    # Get file path based on type
    file_path = None
    results = job.get('results', {})

    if file_type == 'video':
        file_path = results.get('video')
    elif file_type == 'report':
        reports = results.get('reports', [])
        if reports:
            file_path = reports[0]  # Return first report
    elif file_type == 'heatmap':
        heatmaps = results.get('heatmaps', [])
        if heatmaps:
            file_path = heatmaps[0]  # Return first heatmap

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@app.route('/api/analytics/formations/<job_id>', methods=['GET'])
@token_required
@rate_limit(limit_type='analytics', cost=1)
def get_formations(current_user, job_id):
    """Get formation analysis data"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    # Load formation data
    formation_file = os.path.join(job['output_dir'], 'outputs/level3_reports/formation_analysis.json')

    if not os.path.exists(formation_file):
        return jsonify({'error': 'Formation data not found'}), 404

    with open(formation_file, 'r') as f:
        data = json.load(f)

    return jsonify(data), 200


@app.route('/api/analytics/fatigue/<job_id>', methods=['GET'])
@token_required
@rate_limit(limit_type='analytics', cost=1)
def get_fatigue(current_user, job_id):
    """Get fatigue analysis data"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    # Load fatigue data
    fatigue_file = os.path.join(job['output_dir'], 'outputs/level3_reports/fatigue_analysis.json')

    if not os.path.exists(fatigue_file):
        return jsonify({'error': 'Fatigue data not found'}), 404

    with open(fatigue_file, 'r') as f:
        data = json.load(f)

    return jsonify(data), 200


@app.route('/api/analytics/pressing/<job_id>', methods=['GET'])
@token_required
@rate_limit(limit_type='analytics', cost=1)
def get_pressing(current_user, job_id):
    """Get pressing analysis data"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    # Load pressing data
    pressing_file = os.path.join(job['output_dir'], 'outputs/level3_reports/pressing_analysis.json')

    if not os.path.exists(pressing_file):
        return jsonify({'error': 'Pressing data not found'}), 404

    with open(pressing_file, 'r') as f:
        data = json.load(f)

    return jsonify(data), 200


@app.route('/api/analytics/alerts/<job_id>', methods=['GET'])
@token_required
@rate_limit(limit_type='analytics', cost=1)
def get_alerts(current_user, job_id):
    """Get tactical alerts data"""
    if job_id not in jobs_db:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs_db[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': f'Job is {job["status"]}'}), 400

    # Load alerts data
    alerts_file = os.path.join(job['output_dir'], 'outputs/level3_reports/alerts.json')

    if not os.path.exists(alerts_file):
        return jsonify({'error': 'Alerts data not found'}), 404

    with open(alerts_file, 'r') as f:
        data = json.load(f)

    return jsonify(data), 200


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


@app.route('/api/jobs', methods=['GET'])
@token_required
def list_jobs(current_user):
    """List all jobs for current user"""
    user_role = users_db[current_user]['role']

    if user_role == 'admin':
        # Admin can see all jobs
        user_jobs = list(jobs_db.values())
    else:
        # Regular users can only see their own jobs
        user_jobs = [job for job in jobs_db.values() if job['user'] == current_user]

    # Sort by creation date (newest first)
    user_jobs.sort(key=lambda x: x['created_at'], reverse=True)

    return jsonify({
        'jobs': user_jobs,
        'total': len(user_jobs)
    }), 200


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_output_video(output_dir):
    """Find the output video file"""
    video_dir = os.path.join(output_dir, 'output_videos')
    if os.path.exists(video_dir):
        for file in os.listdir(video_dir):
            if file.endswith(('.mp4', '.avi')):
                return os.path.join(video_dir, file)
    return None


def find_reports(output_dir):
    """Find all report files"""
    reports = []
    reports_dir = os.path.join(output_dir, 'outputs/level3_reports')

    if os.path.exists(reports_dir):
        for file in os.listdir(reports_dir):
            if file.endswith('.json'):
                reports.append(os.path.join(reports_dir, file))

    return reports


def find_heatmaps(output_dir):
    """Find all heatmap files"""
    heatmaps = []
    heatmaps_dir = os.path.join(output_dir, 'outputs/heatmaps')

    if os.path.exists(heatmaps_dir):
        for file in os.listdir(heatmaps_dir):
            if file.endswith('.png'):
                heatmaps.append(os.path.join(heatmaps_dir, file))

    return heatmaps


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
