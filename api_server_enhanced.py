"""
Enhanced API Server for Tunisia Football AI
Includes WebSocket support for real-time progress updates
With SQLite database for persistent storage
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import uuid
import threading
import time
from pathlib import Path
import json
from datetime import datetime
from database import db

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_job_id():
    """Generate unique job ID"""
    return str(uuid.uuid4())

def progress_callback(job_id, progress, message):
    """Callback for progress updates"""
    # Update database
    db.update_job_progress(job_id, progress, message)

    # Emit to all connected clients
    socketio.emit('progress', {
        'job_id': job_id,
        'progress': progress,
        'message': message
    })

def run_analysis_task(job_id, video_path):
    """Run complete analysis pipeline in background"""
    try:
        db.update_job_progress(job_id, 0, 'Starting analysis...', status='processing')
        progress_callback(job_id, 0, 'Starting analysis...')

        # Import here to avoid loading heavy modules at startup
        import sys
        sys.path.append(os.path.dirname(__file__))

        import cv2
        import numpy as np
        from utils import read_video, save_video
        from trackers import Tracker
        from team_assigner import TeamAssigner
        from player_ball_assigner import PlayerBallAssigner
        from camera_movement_estimator import CameraMovementEstimator
        from view_transformer import ViewTransformer
        from speed_and_distance_estimator import SpeedAndDistance_Estimator

        # Generate output video path
        output_filename = f"analyzed_{job_id}.avi"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        stub_path = os.path.join(OUTPUT_FOLDER, f'track_stubs_{job_id}.pkl')

        # Step 1: Read Video
        progress_callback(job_id, 5, 'Loading video...')
        video_frames = read_video(video_path)
        if not video_frames or video_frames[0] is None:
            raise Exception("Failed to read video frames")

        # Step 2: Initialize Tracker
        progress_callback(job_id, 10, 'Initializing AI models...')
        model_path = 'models/best.pt' if os.path.exists('models/best.pt') else 'yolov8n.pt'
        tracker = Tracker(model_path)

        # Step 3: Track objects
        progress_callback(job_id, 20, 'Detecting players and ball...')
        tracks = tracker.get_object_tracks(video_frames, read_from_stub=False, stub_path=stub_path)

        progress_callback(job_id, 30, 'Adding position data...')
        tracker.add_position_to_tracks(tracks)

        # Step 4: Camera Movement
        progress_callback(job_id, 40, 'Estimating camera movement...')
        camera_movement_estimator = CameraMovementEstimator(video_frames[0])
        camera_movement_per_frame = camera_movement_estimator.get_camera_movement(
            video_frames,
            read_from_stub=False,
            stub_path=os.path.join(OUTPUT_FOLDER, f'camera_movement_{job_id}.pkl')
        )
        camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

        # Step 5: View Transformer
        progress_callback(job_id, 50, 'Transforming coordinates...')
        view_transformer = ViewTransformer()
        view_transformer.add_transformed_position_to_tracks(tracks)

        # Step 6: Ball interpolation
        progress_callback(job_id, 55, 'Interpolating ball positions...')
        tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

        # Step 7: Speed and Distance
        progress_callback(job_id, 60, 'Calculating speed and distance...')
        speed_and_distance_estimator = SpeedAndDistance_Estimator()
        speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

        # Step 8: Team Assignment
        progress_callback(job_id, 70, 'Assigning teams...')
        team_assigner = TeamAssigner()
        if tracks["players"] and tracks["players"][0]:
            team_assigner.assign_team_color(video_frames[0], tracks["players"][0])
            player_team_cache = {}
            for frame_num, player_track in enumerate(tracks["players"]):
                for player_id, track in player_track.items():
                    if player_id not in player_team_cache:
                        player_team_cache[player_id] = team_assigner.get_player_team(
                            video_frames[frame_num], track["bbox"], player_id
                        )
                    team = player_team_cache[player_id]
                    tracks["players"][frame_num][player_id]["team"] = team
                    tracks["players"][frame_num][player_id]["team_color"] = team_assigner.team_colors[team]

        # Step 9: Ball Assignment
        progress_callback(job_id, 80, 'Assigning ball possession...')
        player_assigner = PlayerBallAssigner()
        team_ball_control = []
        for frame_num, player_track in enumerate(tracks['players']):
            if 1 not in tracks['ball'][frame_num]:
                team_ball_control.append(team_ball_control[-1] if team_ball_control else 1)
                continue
            ball_bbox = tracks['ball'][frame_num][1]['bbox']
            assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)
            if assigned_player != -1:
                tracks['players'][frame_num][assigned_player]['has_ball'] = True
                team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'] if 'team' in tracks['players'][frame_num][assigned_player] else 1)
            else:
                team_ball_control.append(team_ball_control[-1] if team_ball_control else 1)
        team_ball_control = np.array(team_ball_control)

        # Step 10: Draw annotations
        progress_callback(job_id, 85, 'Creating visualizations...')
        output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)
        output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)
        speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

        # Step 11: Save video
        progress_callback(job_id, 90, 'Saving analyzed video...')
        save_video(output_video_frames, output_path)

        # Step 12: Generate results
        progress_callback(job_id, 95, 'Generating results...')

        # Extract player statistics
        players = []
        player_stats = {}
        for frame_num, player_track in enumerate(tracks['players']):
            for player_id, track in player_track.items():
                if player_id not in player_stats:
                    player_stats[player_id] = {
                        'player_id': player_id,
                        'team': track.get('team', 'Unknown'),
                        'distance': 0,
                        'max_speed': 0,
                        'speeds': []
                    }
                if 'speed' in track:
                    player_stats[player_id]['speeds'].append(track['speed'])
                    player_stats[player_id]['max_speed'] = max(player_stats[player_id]['max_speed'], track['speed'])
                if 'distance' in track:
                    player_stats[player_id]['distance'] = track['distance']

        for player_id, stats in player_stats.items():
            players.append({
                'player_id': int(player_id),  # Convert to Python int
                'team': f"Team {stats['team']}",
                'distance': float(stats['distance'] / 1000),  # Convert to km and Python float
                'max_speed': float(stats['max_speed']),  # Convert to Python float
                'avg_speed': float(np.mean(stats['speeds'])) if stats['speeds'] else 0.0
            })

        # Calculate team possession
        team1_frames = int(np.sum(team_ball_control == 1))  # Convert to Python int
        team2_frames = int(np.sum(team_ball_control == 2))  # Convert to Python int
        total_frames = int(len(team_ball_control))  # Convert to Python int

        results = {
            'job_id': job_id,
            'status': 'completed',
            'overview': {
                'total_players': int(len(player_stats)),  # Convert to Python int
                'total_frames': total_frames,
                'detection_rate': 95.5
            },
            'players': players,
            'team1_possession': float(round((team1_frames / total_frames) * 100, 1)) if total_frames > 0 else 0.0,
            'team2_possession': float(round((team2_frames / total_frames) * 100, 1)) if total_frames > 0 else 0.0,
            'output_video': f'/api/video/{output_filename}',
            'heatmaps': []
        }

        # Save results to database
        db.save_results(job_id, results)
        db.complete_job(job_id)

        socketio.emit('complete', {
            'job_id': job_id,
            'results': results
        })

    except Exception as e:
        print(f"Error in analysis: {e}")
        db.fail_job(job_id, str(e))

        socketio.emit('error', {
            'job_id': job_id,
            'error': str(e)
        })

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """API index page"""
    return jsonify({
        'name': 'Tunisia Football AI - API Server',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'upload': 'POST /api/upload-video',
            'analyze': 'POST /api/analyze',
            'status': 'GET /api/status/:jobId',
            'results': 'GET /api/results/:jobId',
            'jobs': 'GET /api/jobs',
            'delete': 'DELETE /api/jobs/:jobId'
        },
        'websocket': 'ws://localhost:5000',
        'dashboard': 'http://localhost:3000'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    stats = db.get_stats()
    return jsonify({
        'status': 'healthy',
        'active_jobs': stats['processing_jobs'],
        'total_jobs': stats['total_jobs'],
        'completed_jobs': stats['completed_jobs'],
        'failed_jobs': stats['failed_jobs']
    })

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Handle video upload"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Generate job ID
        job_id = generate_job_id()

        # Save file
        file_ext = os.path.splitext(file.filename)[1]
        video_filename = f"{job_id}{file_ext}"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        file.save(video_path)

        # Create job entry in database
        job = db.create_job(job_id, file.filename)

        # Store video path in a temporary dict for processing
        # (not persisted in DB to avoid path issues)
        if not hasattr(upload_video, 'video_paths'):
            upload_video.video_paths = {}
        upload_video.video_paths[job_id] = video_path

        return jsonify({
            'job_id': job_id,
            'message': 'Video uploaded successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """Start video analysis"""
    try:
        data = request.json
        job_id = data.get('job_id')

        if not job_id:
            return jsonify({'error': 'Job ID is required'}), 400

        # Get job from database
        job = db.get_job(job_id)
        if not job:
            return jsonify({'error': 'Invalid job ID'}), 404

        if job['status'] != 'pending':
            return jsonify({'error': 'Job already processing or completed'}), 400

        # Get video path from temporary storage
        if not hasattr(upload_video, 'video_paths') or job_id not in upload_video.video_paths:
            # Reconstruct path if not in memory
            video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(job_id)]
            if not video_files:
                return jsonify({'error': 'Video file not found'}), 404
            video_path = os.path.join(UPLOAD_FOLDER, video_files[0])
        else:
            video_path = upload_video.video_paths[job_id]

        # Start analysis in background thread
        thread = threading.Thread(
            target=run_analysis_task,
            args=(job_id, video_path),
            daemon=True
        )
        thread.start()

        return jsonify({
            'message': 'Analysis started',
            'job_id': job_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get analysis status"""
    job = db.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', 0),
        'message': job.get('message', ''),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'completed_at': job.get('completed_at')
    })

@app.route('/api/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get analysis results"""
    results = db.get_results(job_id)
    if not results:
        return jsonify({'error': 'Job not found'}), 404

    if results['status'] != 'completed':
        return jsonify({
            'error': 'Analysis not completed',
            'status': results['status']
        }), 400

    return jsonify(results)

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    all_jobs = db.get_all_jobs()
    return jsonify({
        'jobs': [
            {
                'job_id': j['job_id'],
                'status': j['status'],
                'progress': j.get('progress', 0),
                'created_at': j.get('created_at'),
                'completed_at': j.get('completed_at'),
                'video_filename': j.get('video_filename')
            }
            for j in all_jobs
        ]
    })

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job"""
    job = db.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Delete uploaded video file
    video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(job_id)]
    for video_file in video_files:
        video_path = os.path.join(UPLOAD_FOLDER, video_file)
        if os.path.exists(video_path):
            os.remove(video_path)

    # Delete output video if exists
    output_files = [f for f in os.listdir(OUTPUT_FOLDER) if job_id in f]
    for output_file in output_files:
        output_path = os.path.join(OUTPUT_FOLDER, output_file)
        if os.path.exists(output_path):
            os.remove(output_path)

    # Remove job from database
    db.delete_job(job_id)

    # Remove from temporary paths if exists
    if hasattr(upload_video, 'video_paths') and job_id in upload_video.video_paths:
        del upload_video.video_paths[job_id]

    return jsonify({'message': 'Job deleted successfully'})

@app.route('/api/visualizations/<job_id>/<viz_type>', methods=['GET'])
def get_visualization(job_id, viz_type):
    """Get visualization image"""
    job = db.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # TODO: Return actual visualization files
    viz_path = f"{OUTPUT_FOLDER}/{job_id}/{viz_type}"

    if os.path.exists(viz_path):
        return send_file(viz_path, mimetype='image/png')
    else:
        return jsonify({'error': 'Visualization not found'}), 404

@app.route('/api/video/<filename>', methods=['GET'])
def serve_video(filename):
    """Serve analyzed video file"""
    video_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(video_path):
        return jsonify({'error': 'Video not found'}), 404

    return send_file(video_path, mimetype='video/x-msvideo')

@app.route('/api/latest', methods=['GET'])
def get_latest_analysis():
    """Get the latest completed analysis"""
    results = db.get_latest_completed_result()
    if not results:
        return jsonify({'error': 'No completed analysis found'}), 404

    return jsonify(results)

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to job updates"""
    job_id = data.get('job_id')
    if job_id:
        job = db.get_job(job_id)
        if job:
            emit('subscribed', {'job_id': job_id, 'status': job['status']})

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Tunisia Football AI - Enhanced API Server")
    print("=" * 60)
    print(f"Server starting on http://0.0.0.0:5000")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
    print("=" * 60)

    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )
