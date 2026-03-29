"""
WSGI entry point for production deployment
Use with Gunicorn, uWSGI, or other WSGI servers
"""

from api_server import app

if __name__ == "__main__":
    app.run()
