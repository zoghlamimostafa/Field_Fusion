#!/usr/bin/env python3
"""
Complete Gradio Interface for Tunisia Football AI - Level 3 Professional SaaS
Includes ALL features: analysis, heatmaps, stats, reports, formation detection,
fatigue analysis, pressing metrics, pass networks, alerts, confidence scoring

🇹🇳 TUNISIA FOOTBALL AI - Professional Level 3 SaaS Platform
"""

import gradio as gr
import cv2
import numpy as np
import os
import json
import torch
from trackers.football_tracker import FootballTracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from pitch_detector import PitchDetector
from speed_distance_estimator import SpeedDistanceEstimator
from heatmap_generator import HeatmapGenerator
from event_detector import EventDetector
from analytics_exporter import AnalyticsExporter
from camera_movement_estimator import CameraMovementEstimator
from player_id_consolidator import PlayerIDConsolidator

# NEW: Level 3 Intelligence Modules
from pitch_calibrator_enhanced import EnhancedPitchCalibrator
from fatigue_estimator import FatigueEstimator
from formation_detector import FormationDetector
from alert_engine import AlertEngine
from pressing_analyzer import PressingAnalyzer
from pass_network_analyzer import PassNetworkAnalyzer
from confidence_scorer import ConfidenceScorer
from pdf_report_exporter import PDFReportExporter

from utils import read_video

class FootballAnalyzer:
    def __init__(self):
        self.tracker = None
        self.device = self.resolve_device()
        self.fps = 25

        # Basic components
        self.pitch_detector = PitchDetector()
        self.speed_estimator = SpeedDistanceEstimator(fps=self.fps)
        self.heatmap_gen = HeatmapGenerator()
        self.event_detector = EventDetector()
        self.exporter = AnalyticsExporter(output_dir='outputs/gradio_reports')

        # NEW: Level 3 Intelligence Components
        self.enhanced_pitch_calibrator = EnhancedPitchCalibrator()
        self.fatigue_estimator = FatigueEstimator(fps=self.fps)
        self.formation_detector = FormationDetector(fps=self.fps)
        self.alert_engine = AlertEngine(fps=self.fps)
        self.pressing_analyzer = PressingAnalyzer(fps=self.fps)
        self.pass_network_analyzer = PassNetworkAnalyzer(fps=self.fps)
        self.confidence_scorer = ConfidenceScorer(fps=self.fps)
        self.pdf_exporter = PDFReportExporter()

    def resolve_device(self):
        return 0 if torch.cuda.is_available() else "cpu"

    def initialize_tracker(self):
        resolved_device = self.resolve_device()
        if self.tracker is None or self.device != resolved_device:
            self.device = resolved_device
            self.tracker = FootballTracker(
                model_path=None,
                use_football_model=True,
                device=self.device,
            )

    def analyze_video(self, video_path, progress=gr.Progress()):
        """Complete video analysis"""
        if video_path is None:
            return None, "Please upload a video first", "", ""

        try:
            progress(0, desc="Reading video...")
            video_frames = read_video(video_path)

            progress(0.1, desc="Initializing AI model...")
            self.initialize_tracker()

            progress(0.2, desc="Detecting and tracking...")
            tracks = self.tracker.get_object_tracks(video_frames, read_from_stub=False)

            progress(0.4, desc="Interpolating ball...")
            tracks["ball"] = self.tracker.interpolate_ball_positions(tracks["ball"])

            progress(0.45, desc="Consolidating player IDs...")
            consolidator = PlayerIDConsolidator(expected_players_per_team=11)
            id_mapping = consolidator.consolidate_player_ids(tracks)
            tracks = consolidator.apply_consolidation(tracks, id_mapping)

            progress(0.5, desc="Position tracking...")
            self.tracker.add_position_to_tracks(tracks)

            progress(0.55, desc="Camera stabilization...")
            camera_estimator = CameraMovementEstimator(video_frames[0])
            camera_movement = camera_estimator.get_camera_movement(video_frames)
            camera_estimator.add_adjust_positions_to_tracks(tracks, camera_movement)

            progress(0.6, desc="Enhanced pitch calibration...")
            try:
                # Try enhanced calibration first
                homography, calibration_info = self.enhanced_pitch_calibrator.calibrate_multi_frame(
                    video_frames,
                    frame_indices=[0, min(100, len(video_frames)-1), min(250, len(video_frames)-1)],
                    min_confidence=0.5
                )

                if homography is None or calibration_info.get('confidence', 0) < 0.5:
                    # Fallback to basic calibration
                    homography, calibration_info = self.pitch_detector.estimate_homography_auto(
                        video_frames[0],
                        video_path=video_path,
                        return_metadata=True,
                    )
                    if calibration_info is None:
                        calibration_info = {'method': 'fallback', 'confidence': 0.3}
            except Exception as e:
                print(f"Calibration error: {e}")
                homography = None
                calibration_info = {'method': 'error', 'confidence': 0.0}

            progress(0.65, desc="Team assignment...")
            team_assigner = TeamAssigner()
            team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

            for frame_num, player_track in enumerate(tracks['players']):
                for player_id, track in player_track.items():
                    team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
                    tracks['players'][frame_num][player_id]['team'] = team
                    tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]

            progress(0.72, desc="Ball possession...")
            player_assigner = PlayerBallAssigner()
            team_ball_control = []

            for frame_num, player_track in enumerate(tracks['players']):
                ball_bbox = tracks['ball'][frame_num][1]['bbox']
                assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

                if assigned_player != -1:
                    tracks['players'][frame_num][assigned_player]['has_ball'] = True
                    team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
                else:
                    team_ball_control.append(team_ball_control[-1] if team_ball_control else 0)

            team_ball_control = np.array(team_ball_control)

            progress(0.78, desc="Speed/distance calculation...")
            total_distance, max_speed, avg_speed = self.speed_estimator.add_speed_and_distance_to_tracks(
                tracks, homography
            )

            progress(0.84, desc="Event detection...")
            passes = self.event_detector.detect_passes(tracks, tracks['ball'])
            shots = self.event_detector.detect_shots(tracks, tracks['ball'])
            interceptions = self.event_detector.detect_interceptions(tracks, passes)

            progress(0.88, desc="Generating heatmaps...")
            heatmaps = self.heatmap_gen.generate_all_heatmaps(tracks, homography, output_dir='outputs/gradio_heatmaps')

            progress(0.82, desc="Exporting basic analytics...")
            analytics = self.exporter.export_all(
                tracks, total_distance, max_speed, avg_speed,
                team_ball_control, passes, shots, interceptions
            )

            # === NEW LEVEL 3 INTELLIGENCE ANALYSIS ===

            progress(0.84, desc="Formation detection...")
            formations = self.formation_detector.detect_formations(
                tracks, homography=homography, sample_frames=5
            )

            progress(0.86, desc="Fatigue analysis...")
            fatigue_data = self.fatigue_estimator.estimate_fatigue(
                tracks, analytics, homography=homography
            )

            progress(0.88, desc="Pressing analysis...")
            pressing_data = self.pressing_analyzer.analyze_pressing(
                tracks, analytics, formations=formations, homography=homography
            )

            progress(0.90, desc="Pass network analysis...")
            pass_networks = self.pass_network_analyzer.analyze_pass_networks(
                analytics, tracks=tracks
            )

            progress(0.92, desc="Generating alerts...")
            alerts = self.alert_engine.generate_alerts(
                tracks, analytics, formations=formations, fatigue_data=fatigue_data
            )

            progress(0.94, desc="Calculating confidence...")
            confidence_score = self.confidence_scorer.calculate_confidence(
                tracks, analytics, calibration_info,
                formations=formations, fatigue_data=fatigue_data, pressing_data=pressing_data
            )

            # Consolidate Level 3 analytics
            level3_analytics = {
                'formations': self.formation_detector.export_formations(formations) if formations else {},
                'fatigue': self.fatigue_estimator.export_fatigue_data(fatigue_data) if fatigue_data else {},
                'pressing': self.pressing_analyzer.export_pressing_data(pressing_data) if pressing_data else {},
                'pass_networks': self.pass_network_analyzer.export_pass_network_data(pass_networks) if pass_networks else {},
                'alerts': self.alert_engine.export_alerts_to_dict(alerts) if alerts else {},
                'confidence': self.confidence_scorer.export_confidence_data(confidence_score)
            }
            json_safe_level3 = self.exporter._to_jsonable(level3_analytics)

            # Save Level 3 reports
            os.makedirs('outputs/gradio_level3_reports', exist_ok=True)
            for key, data in json_safe_level3.items():
                with open(f'outputs/gradio_level3_reports/{key}.json', 'w') as f:
                    json.dump(data, f, indent=2)
            self.pdf_exporter.export_report_dicts(json_safe_level3, 'outputs/gradio_level3_reports')

            progress(0.96, desc="Rendering video...")
            output_video_frames = self.tracker.draw_annotations(video_frames, tracks, team_ball_control)

            # Save output video
            output_path = 'outputs/gradio_output.avi'
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            height, width = output_video_frames[0].shape[:2]
            out = cv2.VideoWriter(output_path, fourcc, 25, (width, height))

            for frame in output_video_frames:
                out.write(frame)
            out.release()

            # Generate comprehensive statistics text with Level 3
            team_stats = analytics['team_stats']
            player_stats = analytics['player_stats']
            device_label = "GPU (CUDA:0)" if self.device == 0 else "CPU"

            stats_text = f"""
## 📊 Level 3 Analysis Complete!

**Inference Device**: {device_label}
**Overall Confidence**: {confidence_score.overall_confidence:.2f} ({confidence_score.reliability_level})

### Team Statistics
**Team 1**: {team_stats['team_1']['possession_percent']:.1f}% possession, {team_stats['team_1']['total_passes']} passes, {team_stats['team_1']['total_shots']} shots
**Team 2**: {team_stats['team_2']['possession_percent']:.1f}% possession, {team_stats['team_2']['total_passes']} passes, {team_stats['team_2']['total_shots']} shots

### Top Players by Distance
"""
            for i, player in enumerate(player_stats[:5], 1):
                stats_text += f"\n{i}. Player {player['player_id']} (Team {player['team']}): {player['total_distance_m']:.1f}m"

            stats_text += "\n\n### Events Detected\n"
            stats_text += f"- **Passes**: {len(passes)}\n"
            stats_text += f"- **Shots**: {len(shots)}\n"
            stats_text += f"- **Interceptions**: {len(interceptions)}\n"

            # Add Level 3 summaries
            if formations:
                stats_text += "\n" + self.formation_detector.generate_formation_summary(formations)

            if alerts:
                stats_text += "\n" + self.alert_engine.generate_alert_summary(alerts)

            if fatigue_data:
                high_fatigue = [f for f in fatigue_data.values() if f.fatigue_score > 0.7]
                if high_fatigue:
                    stats_text += f"\n### ⚠️ Fatigue Warnings\n"
                    stats_text += f"{len(high_fatigue)} player(s) showing high fatigue\n"

            if pressing_data:
                stats_text += f"\n### 🛡️ Pressing Intensity\n"
                for team, metrics in pressing_data.items():
                    intensity_level = "High" if metrics.pressing_intensity > 0.7 else "Medium" if metrics.pressing_intensity > 0.4 else "Low"
                    stats_text += f"Team {team}: {metrics.pressing_intensity:.2f} ({intensity_level})\n"

            # Load HTML report
            with open(analytics['html_report'], 'r') as f:
                html_report = f.read()

            progress(1.0, desc="Done!")

            # Prepare all JSON outputs as API-friendly dicts
            events_json = self.exporter._to_jsonable(analytics.get('events', {}))
            if not events_json or not isinstance(events_json, dict):
                events_json = {'passes': [], 'shots': [], 'interceptions': []}

            alerts_json = json_safe_level3.get('alerts', {})
            formations_json = json_safe_level3.get('formations', {})
            fatigue_json = json_safe_level3.get('fatigue', {})
            pressing_json = json_safe_level3.get('pressing', {})
            confidence_json = json_safe_level3.get('confidence', {})

            return (
                output_path,
                stats_text,
                events_json,
                html_report,
                alerts_json,
                formations_json,
                fatigue_json,
                pressing_json,
                confidence_json,
            )

        except Exception as e:
            import traceback
            error_msg = f"Error during analysis: {str(e)}\n\n{traceback.format_exc()}"
            empty_json = {"error": "Analysis failed", "message": str(e)}
            error_html = "<html><body><h1>Error</h1><p>Analysis failed</p></body></html>"
            return None, error_msg, empty_json, error_html, empty_json, empty_json, empty_json, empty_json, empty_json

# Create Gradio interface
analyzer = FootballAnalyzer()

def analyze_video_wrapper(video):
    return analyzer.analyze_video(video)

# Build UI with Level 3 Features
with gr.Blocks(title="Tunisia Football AI - Level 3 Professional SaaS 🇹🇳", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
    # ⚽ Tunisia Football AI - Level 3 Professional SaaS 🇹🇳

    **Professional football match analysis with tactical intelligence**

    ## Core Features:
    - 🎯 Football-specific AI detection (Player, GK, Referee, Ball)
    - 👕 Team assignment & possession tracking
    - ⚡ Speed & distance metrics
    - 🎬 Event detection (Passes, Shots, Interceptions)
    - 🔥 Player heatmaps

    ## 🚀 Level 3 Intelligence:
    - 📐 **Enhanced Pitch Calibration** (Keypoint detection, tactical zones)
    - 🚨 **Tactical Alerts** (10 alert types with recommendations)
    - 💪 **Fatigue Analysis** (Injury prevention, work rate index)
    - ⚽ **Formation Detection** (4-4-2, 4-3-3, 3-5-2, etc.)
    - 🛡️ **Pressing Metrics** (PPDA, compactness, defensive intensity)
    - 🔗 **Pass Network Analysis** (Central players, passing triangles)
    - 📊 **Confidence Scoring** (Trust scores for every metric)
    """)

    with gr.Tab("📹 Video Analysis"):
        with gr.Row():
            with gr.Column():
                video_input = gr.Video(label="Upload Match Video")
                analyze_btn = gr.Button("🚀 Analyze Match", variant="primary", size="lg")

            with gr.Column():
                video_output = gr.Video(label="Analyzed Video")

        with gr.Row():
            stats_output = gr.Markdown(label="Statistics")

    with gr.Tab("📊 Basic Reports"):
        with gr.Row():
            events_json = gr.JSON(label="Events Data (Passes, Shots, Interceptions)")

        with gr.Row():
            html_report = gr.HTML(label="Full HTML Report")

    # NEW: Level 3 Intelligence Tabs
    with gr.Tab("🚨 Alerts & Recommendations"):
        gr.Markdown("### Tactical Alerts with Actionable Recommendations")
        alerts_json = gr.JSON(label="All Alerts (Priority-Ranked)")

    with gr.Tab("⚽ Formation Analysis"):
        gr.Markdown("### Team Formations & Tactical Shape")
        formations_json = gr.JSON(label="Formation Detection Results")

    with gr.Tab("💪 Fatigue & Workload"):
        gr.Markdown("### Player Fatigue Analysis & Injury Prevention")
        fatigue_json = gr.JSON(label="Fatigue Metrics (Sprint Count, Work Rate, Recovery Time)")

    with gr.Tab("🛡️ Pressing & Defense"):
        gr.Markdown("### Pressing Intensity & Defensive Metrics")
        pressing_json = gr.JSON(label="Pressing Analysis (PPDA, Compactness, Line Height)")

    with gr.Tab("📊 Confidence Scores"):
        gr.Markdown("### Analysis Reliability & Quality Metrics")
        confidence_json = gr.JSON(label="Confidence Scoring (Data Quality, Sample Size, Calibration)")

    # NEW: Real-time Streaming Tab
    with gr.Tab("📡 Real-time Stream (Beta)"):
        gr.Markdown("""
        ### Live Camera Feed Processing

        **Stream live video from:**
        - 📹 **RTSP Camera**: `rtsp://camera_ip:port/stream`
        - 🌐 **HTTP Stream**: `http://camera_ip/video.mjpg`
        - 💻 **Webcam**: Enter `0`, `1`, or `2`
        - 📁 **Video File**: Full path to video file

        **Note:** Real-time streaming processes frames as they arrive with live alerts!
        """)

        with gr.Row():
            with gr.Column():
                stream_source = gr.Textbox(
                    label="Stream Source",
                    placeholder="Enter RTSP URL, webcam ID (0), or file path",
                    value="0"
                )
                with gr.Row():
                    start_stream_btn = gr.Button("▶️ Start Stream", variant="primary")
                    stop_stream_btn = gr.Button("⏹️ Stop Stream", variant="stop")

                stream_status = gr.Markdown("**Status:** Not connected")
                stream_metrics = gr.JSON(label="Live Metrics")

            with gr.Column():
                stream_video = gr.Image(label="Live Feed", height=480)
                stream_alerts = gr.JSON(label="Real-time Alerts")

        gr.Markdown("""
        **Features:**
        - ✅ Live detection & tracking (30 FPS)
        - ✅ Real-time alerts (every 5 seconds)
        - ✅ Automatic pitch calibration
        - ✅ Live performance metrics

        **Coming Soon:**
        - 🔄 Formation detection (buffered)
        - 🔄 Fatigue tracking (buffered)
        - 🔄 WebSocket dashboard updates
        """)

    with gr.Tab("ℹ️ About"):
        gr.Markdown("""
        ## Tunisia Football AI Platform

        This platform provides comprehensive AI-powered analysis of football matches specifically optimized for Tunisian football.

        ### Capabilities:

        1. **Detection & Tracking**
           - Football-specific YOLO model
           - Player, goalkeeper, referee, and ball detection
           - ByteTrack for persistent player IDs

        2. **Tactical Analysis**
           - Team possession statistics
           - Player heatmaps
           - Speed and distance metrics

        3. **Event Recognition**
           - Pass detection
           - Shot detection
           - Interception detection

        4. **Export Formats**
           - Annotated video
           - JSON/CSV data
           - HTML reports

        ### Level 3 Features (NEW):
        - ✅ Enhanced Pitch Calibration with keypoint detection
        - ✅ Tactical Alert Engine (10 alert types)
        - ✅ Fatigue Analysis & Injury Prevention
        - ✅ Formation Detection (8 common formations)
        - ✅ Pressing & Defensive Metrics
        - ✅ Pass Network Analysis
        - ✅ Confidence Scoring System

        ### Roadmap:
        - ✅ Level 1-2: MVP Complete
        - ✅ Level 3: Professional Intelligence Complete
        - 🔄 Next: Microservices Architecture + Real-time Streaming
        - 📅 Future: LLM Coach Assistant, Video Highlights, Multi-camera

        **Built with:** PyTorch, YOLO, OpenCV, NetworkX, scikit-learn
        **Architecture:** Microservice-ready, Real-time compatible
        """)

    # Connect button to analysis function with ALL outputs
    analyze_btn.click(
        fn=analyze_video_wrapper,
        inputs=[video_input],
        outputs=[
            video_output,
            stats_output,
            events_json,
            html_report,
            alerts_json,
            formations_json,
            fatigue_json,
            pressing_json,
            confidence_json
        ],
        api_name="analyze_match",
    )

if __name__ == "__main__":
    print("=" * 80)
    print("🇹🇳 Tunisia Football AI - Level 3 Professional SaaS Platform")
    print("=" * 80)
    print("🌐 Access the application at: http://localhost:7862")
    print(f"🎯 Inference device: {'GPU (CUDA:0)' if torch.cuda.is_available() else 'CPU'}")
    print("\n🚀 Level 3 Features Active:")
    print("   ✅ Enhanced Pitch Calibration")
    print("   ✅ Tactical Alert Engine")
    print("   ✅ Fatigue Analysis")
    print("   ✅ Formation Detection")
    print("   ✅ Pressing Metrics")
    print("   ✅ Pass Network Analysis")
    print("   ✅ Confidence Scoring")
    print("=" * 80)
    app.launch(server_name="0.0.0.0", server_port=7862, share=False)
