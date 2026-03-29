# Football AI Analysis API

REST API server for the Football AI Analysis System, providing professional match analysis, tactical intelligence, and real-time analytics.

## Features

- **JWT Authentication** - Secure token-based authentication
- **Rate Limiting** - Token bucket algorithm with configurable limits per endpoint
- **Video Analysis** - Upload and analyze football match videos
- **Tactical Intelligence** - Formation detection, fatigue monitoring, pressing analysis
- **Real-time Analytics** - Access analytical data via REST endpoints
- **Interactive Documentation** - Swagger/OpenAPI documentation at `/api/docs`
- **CORS Support** - Cross-origin resource sharing enabled

## Quick Start

### 1. Installation

```bash
# Install API dependencies
pip install -r api_requirements.txt

# Install core system dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# Secret key for JWT tokens (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-this-in-production

# Server configuration
FLASK_ENV=development
HOST=0.0.0.0
PORT=5000

# File upload limits
MAX_CONTENT_LENGTH=524288000  # 500MB in bytes

# Rate limiting (optional - uses defaults if not set)
RATE_LIMIT_DEFAULT=60
RATE_LIMIT_UPLOAD=5
RATE_LIMIT_ANALYSIS=10
RATE_LIMIT_DOWNLOAD=30
RATE_LIMIT_AUTH=20
RATE_LIMIT_ANALYTICS=100
```

### 3. Run Development Server

```bash
python api_server.py
```

Server will start at `http://localhost:5000`

### 4. Run Production Server

```bash
# Using Gunicorn (recommended for production)
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 api_server:app

# With gevent workers (better for I/O bound tasks)
gunicorn -w 4 -k gevent -b 0.0.0.0:5000 --timeout 300 api_server:app
```

## API Documentation

Interactive API documentation is available at: **http://localhost:5000/api/docs**

The Swagger UI provides:
- Complete endpoint reference
- Request/response schemas
- Try-it-out functionality
- Authentication testing

## Authentication

### Register a New User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password123",
    "role": "user"
  }'
```

Response:
```json
{
  "message": "User registered successfully",
  "username": "john_doe",
  "api_key": "generated-api-key"
}
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "admin",
  "role": "admin",
  "expires_in": 86400
}
```

**Default User:**
- Username: `admin`
- Password: `admin123`

## Usage Examples

### 1. Upload Video

```bash
curl -X POST http://localhost:5000/api/analyze/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "video=@/path/to/match.mp4"
```

Response:
```json
{
  "message": "Video uploaded successfully",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "match.mp4"
}
```

### 2. Start Analysis

```bash
curl -X POST http://localhost:5000/api/analyze/start/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "level": 3
  }'
```

Analysis Levels:
- **Level 1-2**: Basic detection and tracking
- **Level 3**: Professional tactical intelligence (recommended)
- **Level 4**: Advanced analytics (xG, player valuation, injury prediction)

### 3. Check Job Status

```bash
curl -X GET http://localhost:5000/api/analyze/status/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user": "admin",
  "filename": "match.mp4",
  "status": "completed",
  "created_at": "2025-03-28T10:30:00",
  "updated_at": "2025-03-28T10:35:00",
  "analysis_level": 3
}
```

Status Values:
- `uploaded` - Video uploaded, analysis not started
- `processing` - Analysis in progress
- `completed` - Analysis completed successfully
- `failed` - Analysis failed (check error field)

### 4. Get Analysis Results

```bash
curl -X GET http://localhost:5000/api/analyze/results/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Get Formation Analysis

```bash
curl -X GET http://localhost:5000/api/analytics/formations/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "team_1": {
    "formation": "4-4-2",
    "confidence": 0.89,
    "positions": [...]
  },
  "team_2": {
    "formation": "4-3-3",
    "confidence": 0.92,
    "positions": [...]
  }
}
```

### 6. Get Fatigue Analysis

```bash
curl -X GET http://localhost:5000/api/analytics/fatigue/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 7. Get Pressing Analysis

```bash
curl -X GET http://localhost:5000/api/analytics/pressing/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 8. Get Tactical Alerts

```bash
curl -X GET http://localhost:5000/api/analytics/alerts/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 9. Download Results

```bash
# Download analyzed video
curl -X GET http://localhost:5000/api/analyze/download/550e8400-e29b-41d4-a716-446655440000/video \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o analyzed_match.mp4

# Download report
curl -X GET http://localhost:5000/api/analyze/download/550e8400-e29b-41d4-a716-446655440000/report \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o analysis_report.json

# Download heatmap
curl -X GET http://localhost:5000/api/analyze/download/550e8400-e29b-41d4-a716-446655440000/heatmap \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o player_heatmap.png
```

### 10. List All Jobs

```bash
curl -X GET http://localhost:5000/api/jobs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Rate Limiting

The API implements token bucket rate limiting to prevent abuse:

| Endpoint Type | Limit | Burst Limit |
|--------------|-------|-------------|
| Authentication | 20 req/min | 40 |
| Upload | 5 req/min | 10 |
| Analysis | 10 req/min | 20 |
| Analytics | 100 req/min | 200 |
| Download | 30 req/min | 60 |
| Default | 60 req/min | 100 |

When rate limited, the API returns:
- HTTP Status: `429 Too Many Requests`
- Headers:
  - `Retry-After`: Seconds until retry allowed
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Timestamp when limit resets

Example rate limit response:
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again in 15 seconds.",
  "retry_after": 15,
  "limit_type": "upload"
}
```

## API Endpoints Reference

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token

### Video Analysis
- `POST /api/analyze/upload` - Upload video (requires auth)
- `POST /api/analyze/start/<job_id>` - Start analysis (requires auth)
- `GET /api/analyze/status/<job_id>` - Get job status (requires auth)
- `GET /api/analyze/results/<job_id>` - Get analysis results (requires auth)
- `GET /api/analyze/download/<job_id>/<file_type>` - Download files (requires auth)

### Analytics
- `GET /api/analytics/formations/<job_id>` - Get formation data (requires auth)
- `GET /api/analytics/fatigue/<job_id>` - Get fatigue data (requires auth)
- `GET /api/analytics/pressing/<job_id>` - Get pressing data (requires auth)
- `GET /api/analytics/alerts/<job_id>` - Get tactical alerts (requires auth)

### Utility
- `GET /api/health` - Health check (no auth)
- `GET /api/jobs` - List user's jobs (requires auth)

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

Common HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad request (invalid input)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not found
- `413` - Payload too large (file > 500MB)
- `429` - Rate limit exceeded
- `500` - Internal server error

## Security Best Practices

### Production Deployment

1. **Change Secret Key**
   ```env
   SECRET_KEY=use-a-strong-random-secret-key-here
   ```
   Generate a strong key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Use HTTPS**
   - Deploy behind nginx/Apache with SSL
   - Use Let's Encrypt for free SSL certificates

3. **Database**
   - Replace in-memory storage with PostgreSQL/MySQL
   - Use SQLAlchemy for database operations
   - Implement proper user management

4. **Task Queue**
   - Use Celery + Redis for async video processing
   - Prevents request timeouts on long analyses
   - Enables background job processing

5. **File Storage**
   - Use S3/MinIO for video storage
   - Implement file cleanup policies
   - Set up CDN for downloads

6. **Monitoring**
   - Add logging (sentry.io, logstash)
   - Monitor performance (New Relic, DataDog)
   - Set up alerts for failures

7. **CORS Configuration**
   ```python
   # Restrict CORS to specific origins
   CORS(app, resources={
       r"/api/*": {
           "origins": ["https://yourdomain.com"]
       }
   })
   ```

## Integration with Frontend Dashboard

The API is designed to work with the React TypeScript dashboard:

```typescript
// Example: Login and upload video
const API_BASE = 'http://localhost:5000/api';

// 1. Login
const loginResponse = await fetch(`${API_BASE}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin123'
  })
});
const { token } = await loginResponse.json();

// 2. Upload video
const formData = new FormData();
formData.append('video', videoFile);

const uploadResponse = await fetch(`${API_BASE}/analyze/upload`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
const { job_id } = await uploadResponse.json();

// 3. Start analysis
await fetch(`${API_BASE}/analyze/start/${job_id}`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ level: 3 })
});

// 4. Poll for status
const checkStatus = async () => {
  const response = await fetch(`${API_BASE}/analyze/status/${job_id}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  return data.status;
};
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

### Import Errors
```bash
# Ensure all dependencies are installed
pip install -r api_requirements.txt
pip install -r requirements.txt

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### JWT Token Expired
- Tokens expire after 24 hours
- Login again to get a new token
- Implement token refresh in production

### Large File Upload Fails
- Check `MAX_CONTENT_LENGTH` in config
- Increase timeout for Gunicorn: `--timeout 300`
- Consider streaming uploads for very large files

## Performance Optimization

### Async Processing (Recommended)

The current implementation processes videos synchronously. For production, implement async processing:

```bash
# Install Celery and Redis
pip install celery redis

# Run Redis
redis-server

# Run Celery worker
celery -A api_server.celery worker --loglevel=info
```

Example Celery task:
```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def process_video_async(job_id, video_path, output_dir, level):
    # Run analysis in background
    run_complete_pipeline(video_path, output_dir, level)
    # Update job status
    jobs_db[job_id]['status'] = 'completed'
```

## Support

For issues, feature requests, or questions:
- GitHub Issues: [repository link]
- Documentation: `/api/docs`
- Main README: `README.md`

## License

See main project LICENSE file.
