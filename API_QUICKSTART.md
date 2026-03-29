# Football AI API - Quick Start Guide

Get your Football AI Analysis API running in 5 minutes!

## 🚀 Fast Setup

### 1. Install Dependencies

```bash
cd Field_Fusion
pip install -r api_requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env and paste the secret key
nano .env  # or use your preferred editor
```

### 3. Start the Server

```bash
python api_server.py
```

Server runs at: **http://localhost:5000**

API docs at: **http://localhost:5000/api/docs**

## 🧪 Test It Out

### Option 1: Interactive Test Client

```bash
python api_test_client.py
```

Follow the prompts to:
- Login with default credentials
- Upload a video
- Start analysis
- View results

### Option 2: Manual cURL Commands

```bash
# 1. Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Save the token from response
TOKEN="your-token-here"

# 2. Check health
curl http://localhost:5000/api/health

# 3. Upload video
curl -X POST http://localhost:5000/api/analyze/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "video=@path/to/video.mp4"

# Save the job_id from response
JOB_ID="job-id-here"

# 4. Start analysis
curl -X POST http://localhost:5000/api/analyze/start/$JOB_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"level":3}'

# 5. Check status
curl http://localhost:5000/api/analyze/status/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Option 3: Swagger UI

1. Open: http://localhost:5000/api/docs
2. Click "Authorize" button
3. Login to get token
4. Paste token: `Bearer your-token-here`
5. Try endpoints interactively!

## 📝 Default Credentials

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Change these in production!**

## 🎯 Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Get JWT token |
| `/api/analyze/upload` | POST | Upload video |
| `/api/analyze/start/{job_id}` | POST | Start analysis |
| `/api/analyze/status/{job_id}` | GET | Check progress |
| `/api/analytics/formations/{job_id}` | GET | Get formations |
| `/api/analytics/alerts/{job_id}` | GET | Get alerts |
| `/api/docs` | GET | API documentation |

## 🔐 Authentication

All endpoints (except `/api/health` and auth endpoints) require a JWT token:

```bash
Authorization: Bearer <your-token-here>
```

Tokens expire after 24 hours.

## 📊 Analysis Levels

- **Level 1-2:** Basic detection (fast)
- **Level 3:** Professional analysis (recommended)
- **Level 4:** Advanced analytics (slower)

## 🛠️ Production Deployment

### Quick Production Setup

```bash
# 1. Install Gunicorn
pip install gunicorn gevent

# 2. Run with Gunicorn
gunicorn -w 4 -k gevent -b 0.0.0.0:5000 --timeout 300 wsgi:app

# 3. Setup systemd service
sudo cp football-api.service /etc/systemd/system/
sudo systemctl enable football-api
sudo systemctl start football-api

# 4. Setup nginx (optional)
sudo cp nginx.conf.example /etc/nginx/sites-available/football-api
sudo ln -s /etc/nginx/sites-available/football-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find and kill process
lsof -i :5000
kill -9 <PID>
```

### Import Errors

```bash
# Add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Token Expired

```bash
# Login again to get new token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 📚 Documentation

- **Full API Guide:** [API_README.md](API_README.md)
- **Interactive Docs:** http://localhost:5000/api/docs
- **Main Project:** [README.md](README.md)

## 🔥 Rate Limits

| Type | Limit |
|------|-------|
| Auth | 20/min |
| Upload | 5/min |
| Analysis | 10/min |
| Analytics | 100/min |
| Download | 30/min |

Limits are per user/IP.

## 💡 Example: Complete Workflow

```python
from api_test_client import FootballAIClient

# Initialize client
client = FootballAIClient('http://localhost:5000/api')

# Login
client.login('admin', 'admin123')

# Upload and analyze
result = client.upload_video('match.mp4')
job_id = result['job_id']
client.start_analysis(job_id, level=3)

# Wait for completion
client.wait_for_completion(job_id)

# Get results
formations = client.get_formations(job_id)
alerts = client.get_alerts(job_id)

# Download video
client.download_file(job_id, 'video', 'analyzed.mp4')
```

## 🎉 You're Ready!

Start analyzing football matches with professional AI-powered insights!

For more details, see [API_README.md](API_README.md)
