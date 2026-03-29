"""
API Documentation using Flask-RESTX (Swagger/OpenAPI)
Provides interactive API documentation at /api/docs
"""

from flask_restx import Api, Resource, fields, Namespace
from api_server import app

# Initialize API documentation
api = Api(
    app,
    version='1.0.0',
    title='Football AI Analysis API',
    description='''
    Professional Football Match Analysis System API

    Features:
    - Video upload and analysis
    - Real-time tactical intelligence
    - Formation detection
    - Fatigue monitoring
    - Pressing analysis
    - Pass network analysis
    - Tactical alerts

    Authentication:
    All endpoints (except /api/health and auth endpoints) require JWT authentication.
    Include the token in the Authorization header: `Authorization: Bearer <token>`

    Rate Limiting:
    - Auth endpoints: 20 requests/minute
    - Upload endpoints: 5 requests/minute
    - Analysis endpoints: 10 requests/minute
    - Analytics endpoints: 100 requests/minute
    - Download endpoints: 30 requests/minute
    ''',
    doc='/api/docs',
    prefix='/api'
)

# =============================================================================
# MODELS (Request/Response Schemas)
# =============================================================================

# Authentication Models
auth_ns = Namespace('auth', description='Authentication operations')

register_model = auth_ns.model('Register', {
    'username': fields.String(required=True, description='Username', example='john_doe'),
    'password': fields.String(required=True, description='Password', example='secure_password123'),
    'role': fields.String(description='User role (default: user)', example='user', default='user')
})

login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Username', example='admin'),
    'password': fields.String(required=True, description='Password', example='admin123')
})

token_response = auth_ns.model('TokenResponse', {
    'token': fields.String(description='JWT authentication token'),
    'username': fields.String(description='Username'),
    'role': fields.String(description='User role'),
    'expires_in': fields.Integer(description='Token expiration time in seconds')
})

# Analysis Models
analysis_ns = Namespace('analyze', description='Video analysis operations')

upload_response = analysis_ns.model('UploadResponse', {
    'message': fields.String(description='Upload status message'),
    'job_id': fields.String(description='Unique job identifier'),
    'filename': fields.String(description='Uploaded filename')
})

analysis_start_request = analysis_ns.model('AnalysisStartRequest', {
    'level': fields.Integer(
        description='Analysis level (1-4). Level 3 recommended for professional analysis',
        example=3,
        default=3
    )
})

job_status_response = analysis_ns.model('JobStatusResponse', {
    'id': fields.String(description='Job ID'),
    'user': fields.String(description='Username'),
    'filename': fields.String(description='Original filename'),
    'status': fields.String(description='Job status (uploaded, processing, completed, failed)'),
    'created_at': fields.String(description='Job creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp'),
    'analysis_level': fields.Integer(description='Analysis level'),
    'error': fields.String(description='Error message if failed')
})

# Analytics Models
analytics_ns = Namespace('analytics', description='Analytics data operations')

formation_model = analytics_ns.model('Formation', {
    'formation_type': fields.String(description='Detected formation (e.g., 4-4-2, 4-3-3)'),
    'confidence': fields.Float(description='Confidence score (0-1)'),
    'team': fields.String(description='Team name/ID'),
    'timestamp': fields.String(description='Detection timestamp')
})

fatigue_model = analytics_ns.model('Fatigue', {
    'player_id': fields.String(description='Player identifier'),
    'fatigue_level': fields.Float(description='Fatigue level (0-100)'),
    'sprint_count': fields.Integer(description='Number of sprints'),
    'distance_covered': fields.Float(description='Distance covered in meters'),
    'recovery_time': fields.Float(description='Recovery time in seconds'),
    'risk_level': fields.String(description='Injury risk level (low, medium, high)')
})

pressing_model = analytics_ns.model('Pressing', {
    'ppda': fields.Float(description='Passes Per Defensive Action'),
    'defensive_line_height': fields.Float(description='Average defensive line height (meters)'),
    'compactness': fields.Float(description='Team compactness score'),
    'pressure_zones': fields.List(fields.String, description='High pressure zones on pitch')
})

alert_model = analytics_ns.model('Alert', {
    'alert_type': fields.String(description='Type of tactical alert'),
    'severity': fields.String(description='Severity level (info, warning, critical)'),
    'message': fields.String(description='Alert message'),
    'timestamp': fields.String(description='Alert timestamp'),
    'player_id': fields.String(description='Related player ID (if applicable)')
})

# Utility Models
utility_ns = Namespace('utility', description='Utility operations')

health_response = utility_ns.model('HealthResponse', {
    'status': fields.String(description='Service health status'),
    'timestamp': fields.String(description='Current timestamp'),
    'version': fields.String(description='API version')
})

error_response = api.model('ErrorResponse', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message')
})

rate_limit_response = api.model('RateLimitResponse', {
    'error': fields.String(description='Error type', example='Rate limit exceeded'),
    'message': fields.String(description='Error message'),
    'retry_after': fields.Integer(description='Seconds until retry allowed'),
    'limit_type': fields.String(description='Type of rate limit')
})

# =============================================================================
# API ENDPOINTS DOCUMENTATION
# =============================================================================

# Register namespaces
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(analysis_ns, path='/analyze')
api.add_namespace(analytics_ns, path='/analytics')
api.add_namespace(utility_ns, path='/')


# Authentication Endpoints
@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.doc('register_user')
    @auth_ns.expect(register_model)
    @auth_ns.response(201, 'User registered successfully')
    @auth_ns.response(400, 'Bad request', error_response)
    @auth_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def post(self):
        """Register a new user"""
        pass


@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.doc('login_user')
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Login successful', token_response)
    @auth_ns.response(401, 'Invalid credentials', error_response)
    @auth_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def post(self):
        """Login and receive JWT token"""
        pass


# Analysis Endpoints
@analysis_ns.route('/upload')
class UploadVideo(Resource):
    @analysis_ns.doc('upload_video', security='Bearer')
    @analysis_ns.response(201, 'Video uploaded successfully', upload_response)
    @analysis_ns.response(400, 'Bad request', error_response)
    @analysis_ns.response(401, 'Unauthorized', error_response)
    @analysis_ns.response(413, 'File too large', error_response)
    @analysis_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    @analysis_ns.doc(params={
        'video': 'Video file (mp4, avi, mov, mkv, flv, wmv) - Max 500MB'
    })
    def post(self):
        """Upload a video file for analysis"""
        pass


@analysis_ns.route('/start/<string:job_id>')
@analysis_ns.param('job_id', 'The job identifier')
class StartAnalysis(Resource):
    @analysis_ns.doc('start_analysis', security='Bearer')
    @analysis_ns.expect(analysis_start_request)
    @analysis_ns.response(200, 'Analysis started successfully')
    @analysis_ns.response(400, 'Bad request', error_response)
    @analysis_ns.response(401, 'Unauthorized', error_response)
    @analysis_ns.response(404, 'Job not found', error_response)
    @analysis_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def post(self, job_id):
        """Start analysis on uploaded video"""
        pass


@analysis_ns.route('/status/<string:job_id>')
@analysis_ns.param('job_id', 'The job identifier')
class JobStatus(Resource):
    @analysis_ns.doc('get_job_status', security='Bearer')
    @analysis_ns.response(200, 'Success', job_status_response)
    @analysis_ns.response(401, 'Unauthorized', error_response)
    @analysis_ns.response(404, 'Job not found', error_response)
    def get(self, job_id):
        """Get analysis job status"""
        pass


@analysis_ns.route('/results/<string:job_id>')
@analysis_ns.param('job_id', 'The job identifier')
class Results(Resource):
    @analysis_ns.doc('get_results', security='Bearer')
    @analysis_ns.response(200, 'Success')
    @analysis_ns.response(400, 'Job not completed', error_response)
    @analysis_ns.response(401, 'Unauthorized', error_response)
    @analysis_ns.response(404, 'Job not found', error_response)
    def get(self, job_id):
        """Get analysis results"""
        pass


@analysis_ns.route('/download/<string:job_id>/<string:file_type>')
@analysis_ns.param('job_id', 'The job identifier')
@analysis_ns.param('file_type', 'File type (video, report, heatmap)')
class Download(Resource):
    @analysis_ns.doc('download_result', security='Bearer')
    @analysis_ns.response(200, 'File download')
    @analysis_ns.response(400, 'Job not completed', error_response)
    @analysis_ns.response(401, 'Unauthorized', error_response)
    @analysis_ns.response(404, 'File not found', error_response)
    @analysis_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def get(self, job_id, file_type):
        """Download result files"""
        pass


# Analytics Endpoints
@analytics_ns.route('/formations/<string:job_id>')
@analytics_ns.param('job_id', 'The job identifier')
class Formations(Resource):
    @analytics_ns.doc('get_formations', security='Bearer')
    @analytics_ns.response(200, 'Success', [formation_model])
    @analytics_ns.response(400, 'Job not completed', error_response)
    @analytics_ns.response(401, 'Unauthorized', error_response)
    @analytics_ns.response(404, 'Data not found', error_response)
    @analytics_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def get(self, job_id):
        """Get formation analysis data"""
        pass


@analytics_ns.route('/fatigue/<string:job_id>')
@analytics_ns.param('job_id', 'The job identifier')
class Fatigue(Resource):
    @analytics_ns.doc('get_fatigue', security='Bearer')
    @analytics_ns.response(200, 'Success', [fatigue_model])
    @analytics_ns.response(400, 'Job not completed', error_response)
    @analytics_ns.response(401, 'Unauthorized', error_response)
    @analytics_ns.response(404, 'Data not found', error_response)
    @analytics_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def get(self, job_id):
        """Get fatigue analysis data"""
        pass


@analytics_ns.route('/pressing/<string:job_id>')
@analytics_ns.param('job_id', 'The job identifier')
class Pressing(Resource):
    @analytics_ns.doc('get_pressing', security='Bearer')
    @analytics_ns.response(200, 'Success', pressing_model)
    @analytics_ns.response(400, 'Job not completed', error_response)
    @analytics_ns.response(401, 'Unauthorized', error_response)
    @analytics_ns.response(404, 'Data not found', error_response)
    @analytics_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def get(self, job_id):
        """Get pressing analysis data"""
        pass


@analytics_ns.route('/alerts/<string:job_id>')
@analytics_ns.param('job_id', 'The job identifier')
class Alerts(Resource):
    @analytics_ns.doc('get_alerts', security='Bearer')
    @analytics_ns.response(200, 'Success', [alert_model])
    @analytics_ns.response(400, 'Job not completed', error_response)
    @analytics_ns.response(401, 'Unauthorized', error_response)
    @analytics_ns.response(404, 'Data not found', error_response)
    @analytics_ns.response(429, 'Rate limit exceeded', rate_limit_response)
    def get(self, job_id):
        """Get tactical alerts data"""
        pass


# Utility Endpoints
@utility_ns.route('/health')
class Health(Resource):
    @utility_ns.doc('health_check')
    @utility_ns.response(200, 'Service is healthy', health_response)
    def get(self):
        """Health check endpoint"""
        pass


@utility_ns.route('/jobs')
class Jobs(Resource):
    @utility_ns.doc('list_jobs', security='Bearer')
    @utility_ns.response(200, 'Success')
    @utility_ns.response(401, 'Unauthorized', error_response)
    def get(self):
        """List all jobs for current user"""
        pass


# Security scheme
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
    }
}

api.authorizations = authorizations
