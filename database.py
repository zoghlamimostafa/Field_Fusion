"""
Database manager for Football AI Analysis
Uses SQLite for persistent storage of jobs and results
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import threading
from typing import Optional, Dict, List, Any

class DatabaseManager:
    """Thread-safe SQLite database manager for analysis jobs"""

    def __init__(self, db_path: str = "football_analysis.db"):
        self.db_path = db_path
        self.local = threading.local()
        self.init_database()

    def get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                video_filename TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
        ''')

        # Results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                job_id TEXT PRIMARY KEY,
                overview_json TEXT,
                players_json TEXT,
                team1_possession REAL,
                team2_possession REAL,
                output_video TEXT,
                heatmaps_json TEXT,
                phase2_json TEXT,
                phase3_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)')

        conn.commit()

    def create_job(self, job_id: str, video_filename: str) -> Dict[str, Any]:
        """Create a new job entry"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO jobs (job_id, video_filename, status, progress, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, video_filename, 'pending', 0, 'Job created', now, now))

        conn.commit()

        return {
            'job_id': job_id,
            'video_filename': video_filename,
            'status': 'pending',
            'progress': 0,
            'message': 'Job created',
            'created_at': now,
            'updated_at': now
        }

    def update_job_progress(self, job_id: str, progress: int, message: str, status: str = None):
        """Update job progress"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        if status:
            cursor.execute('''
                UPDATE jobs
                SET progress = ?, message = ?, status = ?, updated_at = ?
                WHERE job_id = ?
            ''', (progress, message, status, now, job_id))
        else:
            cursor.execute('''
                UPDATE jobs
                SET progress = ?, message = ?, updated_at = ?
                WHERE job_id = ?
            ''', (progress, message, now, job_id))

        conn.commit()

    def complete_job(self, job_id: str):
        """Mark job as completed"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            UPDATE jobs
            SET status = 'completed', progress = 100, completed_at = ?, updated_at = ?
            WHERE job_id = ?
        ''', (now, now, job_id))

        conn.commit()

    def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            UPDATE jobs
            SET status = 'failed', message = ?, updated_at = ?
            WHERE job_id = ?
        ''', (error_message, now, job_id))

        conn.commit()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs ordered by creation date (newest first)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its results"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
        conn.commit()

        return cursor.rowcount > 0

    def save_results(self, job_id: str, results: Dict[str, Any]):
        """Save analysis results"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Extract data from results
        overview_json = json.dumps(results.get('overview', {}))
        players_json = json.dumps(results.get('players', []))
        team1_possession = results.get('team1_possession', 0.0)
        team2_possession = results.get('team2_possession', 0.0)
        output_video = results.get('output_video', '')
        heatmaps_json = json.dumps(results.get('heatmaps', []))
        phase2_json = json.dumps(results.get('phase2', {})) if results.get('phase2') else None
        phase3_json = json.dumps(results.get('phase3', {})) if results.get('phase3') else None

        # Insert or replace results
        cursor.execute('''
            INSERT OR REPLACE INTO results
            (job_id, overview_json, players_json, team1_possession, team2_possession,
             output_video, heatmaps_json, phase2_json, phase3_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, overview_json, players_json, team1_possession, team2_possession,
              output_video, heatmaps_json, phase2_json, phase3_json, now))

        conn.commit()

    def get_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis results for a job"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get job info
        job = self.get_job(job_id)
        if not job:
            return None

        # Get results
        cursor.execute('SELECT * FROM results WHERE job_id = ?', (job_id,))
        result_row = cursor.fetchone()

        if not result_row:
            return {
                'job_id': job_id,
                'status': job['status'],
                'message': job.get('message', '')
            }

        # Reconstruct results dictionary
        results = {
            'job_id': job_id,
            'status': job['status'],
            'overview': json.loads(result_row['overview_json']) if result_row['overview_json'] else {},
            'players': json.loads(result_row['players_json']) if result_row['players_json'] else [],
            'team1_possession': result_row['team1_possession'],
            'team2_possession': result_row['team2_possession'],
            'output_video': result_row['output_video'],
            'heatmaps': json.loads(result_row['heatmaps_json']) if result_row['heatmaps_json'] else []
        }

        # Add optional phase results
        if result_row['phase2_json']:
            results['phase2'] = json.loads(result_row['phase2_json'])

        if result_row['phase3_json']:
            results['phase3'] = json.loads(result_row['phase3_json'])

        return results

    def get_latest_completed_result(self) -> Optional[Dict[str, Any]]:
        """Get the most recent completed analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT job_id FROM jobs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        ''')

        row = cursor.fetchone()
        if row:
            return self.get_results(row['job_id'])

        return None

    def cleanup_old_jobs(self, days: int = 30):
        """Delete jobs older than specified days"""
        conn = self.get_connection()
        cursor = conn.cursor()

        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute('DELETE FROM jobs WHERE created_at < ?', (cutoff,))
        deleted = cursor.rowcount
        conn.commit()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as total FROM jobs')
        total = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as completed FROM jobs WHERE status = 'completed'")
        completed = cursor.fetchone()['completed']

        cursor.execute("SELECT COUNT(*) as processing FROM jobs WHERE status = 'processing'")
        processing = cursor.fetchone()['processing']

        cursor.execute("SELECT COUNT(*) as failed FROM jobs WHERE status = 'failed'")
        failed = cursor.fetchone()['failed']

        return {
            'total_jobs': total,
            'completed_jobs': completed,
            'processing_jobs': processing,
            'failed_jobs': failed
        }

    def close(self):
        """Close database connection"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')


# Global database instance
db = DatabaseManager()
