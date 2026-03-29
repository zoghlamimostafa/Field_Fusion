#!/usr/bin/env python3
"""
Simple HTTP server to launch the Tunisia Football AI Coach Dashboard
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Configuration
PORT = 8081  # Changed from 8080 due to port conflict
DASHBOARD_FILE = "coach_dashboard_full.html"

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve the dashboard and handle CORS"""

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        # Redirect root to dashboard
        if self.path == '/':
            self.path = f'/{DASHBOARD_FILE}'
        return super().do_GET()

def main():
    # Change to the script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("=" * 60)
    print("Tunisia Football AI - Complete Coach Dashboard")
    print("=" * 60)
    print(f"\n🚀 Starting server on port {PORT}...")
    print(f"📊 Dashboard: http://localhost:{PORT}")
    print(f"📁 Serving from: {script_dir}")
    print("\n✅ FULLY INTEGRATED Dashboard Features:")
    print("   • Team formations & tactical analysis")
    print("   • Pass network & possession metrics")
    print("   • Pressing & defensive statistics")
    print("   • Match events timeline (passes, shots, interceptions)")
    print("   • Player performance & fatigue analysis")
    print("   • AI-powered alerts & insights")
    print("   • Video playback with full reports")
    print("   • Interactive charts & visualizations")
    print("\n📂 Data Sources Integrated:")
    print("   ✓ player_stats.json")
    print("   ✓ team_stats.json")
    print("   ✓ fatigue.json")
    print("   ✓ formations.json")
    print("   ✓ pass_networks.json")
    print("   ✓ pressing.json")
    print("   ✓ events.json")
    print("   ✓ alerts.json")
    print("\n⚠️  Make sure your analysis data is in the 'outputs/' directory")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)

    # Create server
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        # Try to open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            print(f"\n✓ Browser opened automatically")
        except:
            print(f"\n→ Please open http://localhost:{PORT} in your browser")

        print(f"\n🔴 Server is running...")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down server...")
            print("✓ Server stopped successfully\n")

if __name__ == "__main__":
    main()
