import gradio as gr
import cv2
import numpy as np
from utils import read_video, save_video
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator
import os
import tempfile

def process_football_video(video_file, use_stub=True):
    """
    Process a football video and return the annotated version with tracking data.

    Args:
        video_file: Input video file path
        use_stub: Whether to use cached tracking data (faster for demo)

    Returns:
        output_video_path: Path to the annotated output video
        stats: Dictionary with analysis statistics
    """
    if video_file is None:
        return None, "Please upload a video file"

    try:
        # Read Video
        video_frames = read_video(video_file)
        print(f"Read {len(video_frames)} frames from video")

        if not video_frames:
            return None, "Error: Could not read video frames"

        # Initialize Tracker
        model_path = 'models/best.pt' if os.path.exists('models/best.pt') else 'yolov8n.pt'
        tracker = Tracker(model_path)

        # Get object tracks
        stub_path = 'stubs/track_stubs.pkl'
        tracks = tracker.get_object_tracks(video_frames, read_from_stub=use_stub, stub_path=stub_path)

        # Add positions to tracks
        tracker.add_position_to_tracks(tracks)

        # Camera Movement Estimator
        camera_movement_estimator = CameraMovementEstimator(video_frames[0])
        camera_movement_per_frame = camera_movement_estimator.get_camera_movement(
            video_frames,
            read_from_stub=use_stub,
            stub_path='stubs/camera_movement_stub.pkl'
        )
        camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

        # View Transformer
        view_transformer = ViewTransformer()
        view_transformer.add_transformed_position_to_tracks(tracks)

        # Interpolate Ball Positions
        tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

        # Speed and distance estimator
        speed_and_distance_estimator = SpeedAndDistance_Estimator()
        speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

        # Assign Player Teams
        team_assigner = TeamAssigner()
        if tracks["players"] and tracks["players"][0]:
            team_assigner.assign_team_color(video_frames[0], tracks["players"][0])

            for frame_num, player_track in enumerate(tracks["players"]):
                for player_id, track in player_track.items():
                    team = team_assigner.get_player_team(video_frames[frame_num], track["bbox"], player_id)
                    tracks["players"][frame_num][player_id]["team"] = team
                    tracks["players"][frame_num][player_id]["team_color"] = team_assigner.team_colors[team]

        # Assign Ball Possession
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

        # Draw annotations
        output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)
        output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)
        speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

        # Save output video to temporary file
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.avi').name
        save_video(output_video_frames, output_path)

        # Calculate statistics
        team1_possession = (team_ball_control == 1).sum()
        team2_possession = (team_ball_control == 2).sum()
        total_possession = team1_possession + team2_possession

        team1_pct = (team1_possession / total_possession * 100) if total_possession > 0 else 0
        team2_pct = (team2_possession / total_possession * 100) if total_possession > 0 else 0

        stats_text = f"""
        ## Analysis Results

        **Total Frames Processed:** {len(video_frames)}

        **Ball Possession:**
        - Team 1: {team1_pct:.1f}%
        - Team 2: {team2_pct:.1f}%

        **Players Tracked:** {len(tracks['players'][0]) if tracks['players'] else 0}

        **Analysis Complete!** ✅
        """

        return output_path, stats_text

    except Exception as e:
        return None, f"Error processing video: {str(e)}"


# Create Gradio Interface
with gr.Blocks(title="Football Analysis - Field Fusion", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # ⚽ Football Analysis - Field Fusion

        Upload a football video to analyze player movements, track the ball, detect teams,
        and calculate speeds and distances in real-time!

        **Features:**
        - Player & Ball Tracking
        - Team Detection
        - Ball Possession Analysis
        - Speed & Distance Calculations
        - Camera Movement Compensation
        """
    )

    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="Upload Football Video")
            use_cache = gr.Checkbox(label="Use Cached Tracking Data (Faster)", value=True)
            analyze_btn = gr.Button("Analyze Video", variant="primary", size="lg")

        with gr.Column():
            video_output = gr.Video(label="Annotated Output")
            stats_output = gr.Markdown(label="Analysis Statistics")

    gr.Markdown(
        """
        ### 📊 What You'll See:
        - **Bounding boxes** around players and ball
        - **Team colors** assigned automatically
        - **Speed indicators** showing player velocity
        - **Ball possession** statistics overlay
        - **Distance covered** by each player
        """
    )

    # Set up event handler
    analyze_btn.click(
        fn=process_football_video,
        inputs=[video_input, use_cache],
        outputs=[video_output, stats_output]
    )

    gr.Markdown(
        """
        ---
        **Note:** First-time analysis may take longer as it downloads the AI model.
        Enable "Use Cached Tracking Data" for faster processing on demo videos.
        """
    )

# Launch the app
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
