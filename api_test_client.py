"""
Test client for Football AI Analysis API
Demonstrates how to use the API endpoints
"""

import requests
import time
import json
from pathlib import Path


class FootballAIClient:
    """Python client for Football AI Analysis API"""

    def __init__(self, base_url='http://localhost:5000/api'):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def _get_headers(self, include_auth=True):
        """Get request headers"""
        headers = {}
        if include_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def register(self, username, password, role='user'):
        """Register a new user"""
        url = f'{self.base_url}/auth/register'
        data = {
            'username': username,
            'password': password,
            'role': role
        }

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def login(self, username, password):
        """Login and store JWT token"""
        url = f'{self.base_url}/auth/login'
        data = {
            'username': username,
            'password': password
        }

        response = self.session.post(url, json=data)
        response.raise_for_status()

        result = response.json()
        self.token = result['token']
        return result

    def upload_video(self, video_path):
        """Upload a video file"""
        url = f'{self.base_url}/analyze/upload'
        headers = self._get_headers()

        with open(video_path, 'rb') as f:
            files = {'video': f}
            response = self.session.post(url, headers=headers, files=files)

        response.raise_for_status()
        return response.json()

    def start_analysis(self, job_id, level=3):
        """Start analysis on uploaded video"""
        url = f'{self.base_url}/analyze/start/{job_id}'
        headers = self._get_headers()
        headers['Content-Type'] = 'application/json'

        data = {'level': level}
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_job_status(self, job_id):
        """Get job status"""
        url = f'{self.base_url}/analyze/status/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, job_id, poll_interval=5, timeout=600):
        """Wait for analysis to complete"""
        start_time = time.time()

        while True:
            status_data = self.get_job_status(job_id)
            status = status_data['status']

            print(f"Job {job_id} status: {status}")

            if status == 'completed':
                return status_data
            elif status == 'failed':
                raise Exception(f"Analysis failed: {status_data.get('error')}")

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Analysis timeout after {timeout} seconds")

            time.sleep(poll_interval)

    def get_results(self, job_id):
        """Get analysis results"""
        url = f'{self.base_url}/analyze/results/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_formations(self, job_id):
        """Get formation analysis"""
        url = f'{self.base_url}/analytics/formations/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_fatigue(self, job_id):
        """Get fatigue analysis"""
        url = f'{self.base_url}/analytics/fatigue/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_pressing(self, job_id):
        """Get pressing analysis"""
        url = f'{self.base_url}/analytics/pressing/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_alerts(self, job_id):
        """Get tactical alerts"""
        url = f'{self.base_url}/analytics/alerts/{job_id}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def download_file(self, job_id, file_type, output_path):
        """Download result file"""
        url = f'{self.base_url}/analyze/download/{job_id}/{file_type}'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    def list_jobs(self):
        """List all jobs"""
        url = f'{self.base_url}/jobs'
        headers = self._get_headers()

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def health_check(self):
        """Check API health"""
        url = f'{self.base_url}/health'
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


def main():
    """Example usage"""
    print("Football AI Analysis API - Test Client")
    print("=" * 50)

    # Initialize client
    client = FootballAIClient('http://localhost:5000/api')

    # Health check
    print("\n1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Version: {health['version']}")

    # Login
    print("\n2. Logging in...")
    try:
        login_result = client.login('admin', 'admin123')
        print(f"   Username: {login_result['username']}")
        print(f"   Role: {login_result['role']}")
        print(f"   Token expires in: {login_result['expires_in']} seconds")
    except requests.exceptions.HTTPError as e:
        print(f"   Login failed: {e}")
        return

    # Upload video (example - replace with actual video path)
    video_path = input("\n3. Enter path to video file (or press Enter to skip): ").strip()

    if video_path and Path(video_path).exists():
        print(f"   Uploading {video_path}...")
        try:
            upload_result = client.upload_video(video_path)
            job_id = upload_result['job_id']
            print(f"   Job ID: {job_id}")
            print(f"   Filename: {upload_result['filename']}")

            # Start analysis
            print("\n4. Starting analysis (Level 3)...")
            client.start_analysis(job_id, level=3)
            print("   Analysis started!")

            # Wait for completion
            print("\n5. Waiting for analysis to complete...")
            print("   This may take several minutes...")
            status_data = client.wait_for_completion(job_id, poll_interval=10)
            print(f"   Analysis completed at: {status_data['updated_at']}")

            # Get results
            print("\n6. Fetching results...")
            results = client.get_results(job_id)
            print(f"   Results: {json.dumps(results, indent=2)}")

            # Get analytics
            print("\n7. Fetching analytics...")
            try:
                formations = client.get_formations(job_id)
                print(f"   Formations: {json.dumps(formations, indent=2)[:200]}...")
            except:
                print("   Formation data not available")

            try:
                alerts = client.get_alerts(job_id)
                print(f"   Alerts: {len(alerts.get('alerts', []))} alerts found")
            except:
                print("   Alerts data not available")

            # Download video
            print("\n8. Downloading analyzed video...")
            download_choice = input("   Download video? (y/n): ").strip().lower()
            if download_choice == 'y':
                output_path = f"downloaded_{job_id}.mp4"
                client.download_file(job_id, 'video', output_path)
                print(f"   Video saved to: {output_path}")

        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("   Skipping video upload")

    # List jobs
    print("\n9. Listing all jobs...")
    jobs = client.list_jobs()
    print(f"   Total jobs: {jobs['total']}")
    for job in jobs['jobs'][:5]:  # Show first 5
        print(f"   - {job['filename']} ({job['status']}) - {job['created_at']}")

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
