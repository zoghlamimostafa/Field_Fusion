#!/usr/bin/env python3
"""
Video Upload and Analysis Server
Handles video uploads and triggers the analysis pipeline
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / 'input_videos'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the upload dashboard"""
    return send_from_directory('.', 'dashboard_upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video upload"""
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: MP4, AVI, MOV, MKV'}), 400

        # Get form data
        match_name = request.form.get('matchName', 'Unknown Match')
        match_date = request.form.get('matchDate', datetime.now().strftime('%Y-%m-%d'))
        team1_name = request.form.get('team1Name', 'Team 1')
        team2_name = request.form.get('team2Name', 'Team 2')

        # Parse analysis options
        options = {
            'formation': request.form.get('optionFormation') == 'true',
            'fatigue': request.form.get('optionFatigue') == 'true',
            'passing': request.form.get('optionPassing') == 'true',
            'pressing': request.form.get('optionPressing') == 'true',
            'events': request.form.get('optionEvents') == 'true',
            'heatmap': request.form.get('optionHeatmap') == 'true',
        }

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        filepath = UPLOAD_FOLDER / safe_filename

        file.save(str(filepath))

        # Save match metadata
        metadata = {
            'match_name': match_name,
            'match_date': match_date,
            'team1_name': team1_name,
            'team2_name': team2_name,
            'video_file': safe_filename,
            'upload_time': timestamp,
            'options': options
        }

        metadata_file = UPLOAD_FOLDER / f"{timestamp}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        return jsonify({
            'success': True,
            'message': 'Video uploaded successfully',
            'filename': safe_filename,
            'file_size': os.path.getsize(filepath),
            'metadata': metadata
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """Start video analysis pipeline"""
    try:
        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        video_path = UPLOAD_FOLDER / filename
        if not video_path.exists():
            return jsonify({'error': 'Video file not found'}), 404

        # Load metadata
        timestamp = filename.split('_')[0]
        metadata_file = UPLOAD_FOLDER / f"{timestamp}_metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        # Prepare analysis command
        cmd = [
            'python3',
            'complete_pipeline.py',
            '--input', str(video_path),
            '--output-dir', str(OUTPUT_FOLDER)
        ]

        # Add options based on metadata
        options = metadata.get('options', {})
        if not options.get('formation', True):
            cmd.append('--no-formation')
        if not options.get('fatigue', True):
            cmd.append('--no-fatigue')
        if not options.get('heatmap', True):
            cmd.append('--no-heatmap')

        # Start analysis in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent
        )

        return jsonify({
            'success': True,
            'message': 'Analysis started',
            'process_id': process.pid,
            'video_file': filename,
            'metadata': metadata
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<int:process_id>', methods=['GET'])
def check_status(process_id):
    """Check analysis status"""
    try:
        # Check if process is still running
        import psutil

        if psutil.pid_exists(process_id):
            return jsonify({
                'status': 'running',
                'process_id': process_id
            })
        else:
            return jsonify({
                'status': 'complete',
                'process_id': process_id
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent', methods=['GET'])
def get_recent_analyses():
    """Get list of recent analyses"""
    try:
        analyses = []

        # Read metadata files
        for metadata_file in sorted(UPLOAD_FOLDER.glob('*_metadata.json'), reverse=True):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Check if output exists
            output_exists = (OUTPUT_FOLDER / 'gradio_reports' / 'player_stats.json').exists()

            analyses.append({
                'match_name': metadata.get('match_name', 'Unknown'),
                'match_date': metadata.get('match_date', 'N/A'),
                'team1': metadata.get('team1_name', 'Team 1'),
                'team2': metadata.get('team2_name', 'Team 2'),
                'upload_time': metadata.get('upload_time', 'N/A'),
                'video_file': metadata.get('video_file', 'N/A'),
                'status': 'complete' if output_exists else 'pending'
            })

        return jsonify({
            'success': True,
            'analyses': analyses[:10]  # Return last 10
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-pdfs', methods=['POST'])
def generate_pdfs():
    """Generate human-readable PDFs"""
    try:
        cmd = ['python3', 'generate_readable_pdfs.py']

        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'PDFs generated successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'error': 'PDF generation failed',
                'details': result.stderr
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Tunisia Football AI - Upload Server")
    print("=" * 60)
    print("\n🚀 Starting upload server...")
    print("📊 Upload Dashboard: http://localhost:5000")
    print("📁 Upload folder:", UPLOAD_FOLDER)
    print("📁 Output folder:", OUTPUT_FOLDER)
    print("\n⚠️  Max file size: 500MB")
    print("✅ Allowed formats: MP4, AVI, MOV, MKV")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
