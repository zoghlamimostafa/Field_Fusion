"""
Real-time Football Analysis System
Processes webcam/stream video feed in real-time using pretrained models
"""
import cv2
import numpy as np
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator
import os
import time
from collections import deque


class RealtimeFootballAnalyzer:
    """Real-time football analysis using pretrained models"""

    def __init__(self, model_path='yolov8n.pt', use_gpu=True):
        """
        Initialize real-time analyzer

        Args:
            model_path: Path to YOLO model
            use_gpu: Whether to use GPU acceleration
        """
        print("🚀 Initializing Real-time Football Analyzer...")

        # Initialize tracker with pretrained model
        self.tracker = Tracker(model_path)
        print(f"✅ Loaded model: {model_path}")

        # Initialize team assigner
        self.team_assigner = TeamAssigner()
        self.team_colors_initialized = False

        # Initialize ball assigner
        self.player_assigner = PlayerBallAssigner()

        # Initialize view transformer
        self.view_transformer = ViewTransformer()

        # Initialize speed/distance estimator
        self.speed_estimator = SpeedAndDistance_Estimator()

        # Track history for smooth processing
        self.track_history = deque(maxlen=30)  # Keep last 30 frames
        self.ball_history = deque(maxlen=10)
        self.team_ball_control = []

        # Performance metrics
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

        print("✅ Real-time analyzer ready!")

    def process_frame(self, frame):
        """
        Process a single frame in real-time

        Args:
            frame: Input video frame (numpy array)

        Returns:
            annotated_frame: Frame with tracking annotations
            stats: Dictionary with current statistics
        """
        if frame is None:
            return None, {}

        # Track objects in current frame
        tracks = self.tracker.get_object_tracks(
            [frame],
            read_from_stub=False,
            stub_path=None
        )

        # Initialize team colors on first frame with players
        if not self.team_colors_initialized and tracks["players"] and tracks["players"][0]:
            self.team_assigner.assign_team_color(frame, tracks["players"][0])
            self.team_colors_initialized = True
            print("✅ Team colors initialized")

        # Process current frame
        current_frame_data = {
            'players': tracks["players"][0] if tracks["players"] else {},
            'ball': tracks["ball"][0] if tracks["ball"] else {},
            'referees': tracks["referees"][0] if tracks["referees"] else {}
        }

        # Add positions to tracks
        self.tracker.add_position_to_tracks(tracks)

        # Assign teams to players
        if self.team_colors_initialized and current_frame_data['players']:
            for player_id, track in current_frame_data['players'].items():
                team = self.team_assigner.get_player_team(
                    frame,
                    track["bbox"],
                    player_id
                )
                current_frame_data['players'][player_id]["team"] = team
                current_frame_data['players'][player_id]["team_color"] = \
                    self.team_assigner.team_colors[team]

        # Assign ball possession
        team_control = 1  # Default
        if current_frame_data['players'] and 1 in current_frame_data['ball']:
            ball_bbox = current_frame_data['ball'][1]['bbox']
            assigned_player = self.player_assigner.assign_ball_to_player(
                current_frame_data['players'],
                ball_bbox
            )

            if assigned_player != -1 and 'team' in current_frame_data['players'][assigned_player]:
                current_frame_data['players'][assigned_player]['has_ball'] = True
                team_control = current_frame_data['players'][assigned_player]['team']

        self.team_ball_control.append(team_control)

        # Draw annotations
        annotated_frame = frame.copy()

        # Draw player boxes
        for player_id, track in current_frame_data['players'].items():
            bbox = track['bbox']
            x1, y1, x2, y2 = map(int, bbox)

            # Get team color
            color = track.get('team_color', (255, 255, 255))

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # Draw player ID
            text = f"P{player_id}"
            if 'team' in track:
                text += f" T{track['team']}"
            cv2.putText(
                annotated_frame,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

            # Draw ball possession indicator
            if track.get('has_ball', False):
                cv2.circle(annotated_frame, (x1 + 10, y1 + 10), 8, (0, 255, 0), -1)

        # Draw ball
        if 1 in current_frame_data['ball']:
            bbox = current_frame_data['ball'][1]['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            cv2.circle(annotated_frame, center, 10, (0, 255, 255), -1)
            cv2.circle(annotated_frame, center, 12, (0, 0, 255), 2)

        # Draw referees
        for ref_id, track in current_frame_data['referees'].items():
            bbox = track['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 0), 2)
            cv2.putText(
                annotated_frame,
                f"REF{ref_id}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )

        # Calculate and draw statistics
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        self.fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0

        # Calculate possession stats
        if len(self.team_ball_control) > 0:
            team1_poss = sum(1 for t in self.team_ball_control if t == 1)
            team2_poss = sum(1 for t in self.team_ball_control if t == 2)
            total = team1_poss + team2_poss

            team1_pct = (team1_poss / total * 100) if total > 0 else 0
            team2_pct = (team2_poss / total * 100) if total > 0 else 0
        else:
            team1_pct = team2_pct = 0

        # Draw info overlay
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0, annotated_frame)

        # Draw text info
        y_offset = 35
        cv2.putText(annotated_frame, f"FPS: {self.fps:.1f}", (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        y_offset += 30
        cv2.putText(annotated_frame, f"Players: {len(current_frame_data['players'])}",
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        y_offset += 30
        cv2.putText(annotated_frame, f"Team 1: {team1_pct:.1f}%",
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)

        y_offset += 30
        cv2.putText(annotated_frame, f"Team 2: {team2_pct:.1f}%",
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)

        stats = {
            'fps': self.fps,
            'players': len(current_frame_data['players']),
            'team1_possession': team1_pct,
            'team2_possession': team2_pct
        }

        return annotated_frame, stats


def main_webcam():
    """Run real-time analysis on webcam feed"""
    print("🎥 Starting webcam analysis...")

    # Initialize analyzer
    analyzer = RealtimeFootballAnalyzer()

    # Open webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Error: Could not open webcam")
        return

    print("✅ Webcam opened. Press 'q' to quit, 's' to save screenshot")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        # Process frame
        annotated_frame, stats = analyzer.process_frame(frame)

        # Display
        cv2.imshow('Real-time Football Analysis', annotated_frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            filename = f"screenshot_{int(time.time())}.jpg"
            cv2.imwrite(filename, annotated_frame)
            print(f"📸 Screenshot saved: {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Real-time analysis ended")


def main_video(video_path):
    """Run real-time analysis on video file"""
    print(f"🎥 Starting video analysis: {video_path}")

    # Initialize analyzer
    analyzer = RealtimeFootballAnalyzer()

    # Open video
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"❌ Error: Could not open video: {video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"📹 Video: {fps} FPS, {total_frames} frames")
    print("✅ Press 'q' to quit, 's' to save screenshot, SPACE to pause")

    paused = False

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("✅ Video ended")
                break

            # Process frame
            current_frame = frame
            annotated_frame, stats = analyzer.process_frame(frame)
        else:
            # Keep showing last frame when paused
            annotated_frame, stats = analyzer.process_frame(current_frame)

        # Display
        cv2.imshow('Real-time Football Analysis', annotated_frame)

        # Handle key presses
        key = cv2.waitKey(1 if not paused else 100) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            filename = f"screenshot_{int(time.time())}.jpg"
            cv2.imwrite(filename, annotated_frame)
            print(f"📸 Screenshot saved: {filename}")
        elif key == ord(' '):
            paused = not paused
            print("⏸ Paused" if paused else "▶ Playing")

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Video analysis ended")


def main_stream(stream_url):
    """Run real-time analysis on network stream (RTSP/HTTP)"""
    print(f"🌐 Starting stream analysis: {stream_url}")

    # Initialize analyzer
    analyzer = RealtimeFootballAnalyzer()

    # Open stream
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print(f"❌ Error: Could not open stream: {stream_url}")
        return

    print("✅ Stream opened. Press 'q' to quit, 's' to save screenshot")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠ Stream interrupted, reconnecting...")
            cap.release()
            cap = cv2.VideoCapture(stream_url)
            continue

        # Process frame
        annotated_frame, stats = analyzer.process_frame(frame)

        # Display
        cv2.imshow('Real-time Football Analysis', annotated_frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            filename = f"screenshot_{int(time.time())}.jpg"
            cv2.imwrite(filename, annotated_frame)
            print(f"📸 Screenshot saved: {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Stream analysis ended")


if __name__ == "__main__":
    import sys

    print("""
    ⚽ Real-time Football Analysis System
    =====================================

    Usage:
        python realtime_app.py                    # Use webcam
        python realtime_app.py video.mp4          # Analyze video file
        python realtime_app.py rtsp://stream      # Analyze network stream

    Controls:
        q     - Quit
        s     - Save screenshot
        SPACE - Pause/Resume (video only)
    """)

    if len(sys.argv) == 1:
        # No arguments - use webcam
        main_webcam()
    else:
        source = sys.argv[1]

        # Check if it's a stream URL
        if source.startswith('rtsp://') or source.startswith('http://') or source.startswith('https://'):
            main_stream(source)
        elif os.path.exists(source):
            # It's a video file
            main_video(source)
        else:
            print(f"❌ Error: File not found: {source}")
            print("💡 Usage: python realtime_app.py [webcam|video.mp4|rtsp://stream]")
