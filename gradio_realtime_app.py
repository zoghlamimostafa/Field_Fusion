"""
Real-time Football Analysis with Gradio Streaming Interface
"""
import gradio as gr
import cv2
import numpy as np
from realtime_app import RealtimeFootballAnalyzer
import time


class GradioRealtimeAnalyzer:
    """Wrapper for Gradio real-time streaming"""

    def __init__(self):
        self.analyzer = None
        self.is_running = False

    def process_webcam_stream(self):
        """Process webcam stream for Gradio"""
        if self.analyzer is None:
            self.analyzer = RealtimeFootballAnalyzer()

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            yield None, "Error: Could not open webcam"
            return

        self.is_running = True

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break

            # Process frame
            annotated_frame, stats = self.analyzer.process_frame(frame)

            # Convert BGR to RGB for Gradio
            annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            # Create stats text
            stats_text = f"""
            ### 📊 Real-time Stats

            **FPS:** {stats['fps']:.1f}
            **Players Detected:** {stats['players']}
            **Team 1 Possession:** {stats['team1_possession']:.1f}%
            **Team 2 Possession:** {stats['team2_possession']:.1f}%
            """

            yield annotated_frame_rgb, stats_text

            time.sleep(0.03)  # ~30 FPS

        cap.release()

    def process_video_stream(self, video_file):
        """Process uploaded video stream for Gradio"""
        if video_file is None:
            yield None, "Please upload a video file"
            return

        if self.analyzer is None:
            self.analyzer = RealtimeFootballAnalyzer()

        cap = cv2.VideoCapture(video_file)

        if not cap.isOpened():
            yield None, f"Error: Could not open video: {video_file}"
            return

        self.is_running = True
        frame_count = 0

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Process every frame for smooth playback
            annotated_frame, stats = self.analyzer.process_frame(frame)

            # Convert BGR to RGB for Gradio
            annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            # Create stats text
            stats_text = f"""
            ### 📊 Real-time Stats

            **Frame:** {frame_count}
            **FPS:** {stats['fps']:.1f}
            **Players:** {stats['players']}
            **Team 1:** {stats['team1_possession']:.1f}%
            **Team 2:** {stats['team2_possession']:.1f}%
            """

            yield annotated_frame_rgb, stats_text

            # Control playback speed
            time.sleep(0.033)  # ~30 FPS

        cap.release()

    def stop_stream(self):
        """Stop the current stream"""
        self.is_running = False


# Create Gradio interface
with gr.Blocks(title="Real-time Football Analysis") as demo:
    gr.Markdown(
        """
        # ⚽ Real-time Football Analysis

        Process live webcam feed or video files with AI-powered football analysis!
        """
    )

    analyzer = GradioRealtimeAnalyzer()

    with gr.Tabs():
        # Tab 1: Webcam Stream
        with gr.Tab("📹 Webcam Stream"):
            gr.Markdown("### Live webcam analysis with real-time tracking")

            with gr.Row():
                webcam_output = gr.Image(label="Live Analysis", streaming=True)
                webcam_stats = gr.Markdown("### Waiting for stream...")

            with gr.Row():
                start_webcam_btn = gr.Button("Start Webcam", variant="primary")
                stop_webcam_btn = gr.Button("Stop", variant="stop")

            start_webcam_btn.click(
                fn=analyzer.process_webcam_stream,
                outputs=[webcam_output, webcam_stats]
            )
            stop_webcam_btn.click(fn=analyzer.stop_stream)

        # Tab 2: Video File Stream
        with gr.Tab("🎬 Video File"):
            gr.Markdown("### Upload a video for real-time analysis")

            video_input = gr.Video(label="Upload Football Video")

            with gr.Row():
                video_output = gr.Image(label="Analysis Stream", streaming=True)
                video_stats = gr.Markdown("### Upload a video to start")

            with gr.Row():
                start_video_btn = gr.Button("Start Analysis", variant="primary")
                stop_video_btn = gr.Button("Stop", variant="stop")

            start_video_btn.click(
                fn=analyzer.process_video_stream,
                inputs=[video_input],
                outputs=[video_output, video_stats]
            )
            stop_video_btn.click(fn=analyzer.stop_stream)

        # Tab 3: Information
        with gr.Tab("ℹ️ Info"):
            gr.Markdown(
                """
                ## Features

                ### Real-time Detection:
                - **Player Tracking** - Track all players with unique IDs
                - **Ball Detection** - Locate and track the ball
                - **Team Classification** - Automatic team color detection
                - **Ball Possession** - Show which team controls the ball
                - **Performance Stats** - FPS and player counts

                ### How to Use:

                #### Webcam Mode:
                1. Click "Start Webcam" button
                2. Allow browser access to camera
                3. Point camera at football match (TV, phone, etc.)
                4. See real-time analysis!

                #### Video File Mode:
                1. Upload a football video
                2. Click "Start Analysis"
                3. Watch the stream with live annotations

                ### Controls:
                - **Stop button** - Stop current stream
                - All processing happens in real-time using pretrained YOLO models

                ### Technical Details:
                - **Model:** YOLOv8n (pretrained)
                - **Tracking:** ByteTrack algorithm
                - **Team Detection:** K-means clustering on jersey colors
                - **Target FPS:** ~30 FPS (depending on hardware)

                ### Tips for Best Results:
                - Good lighting conditions
                - Clear view of the field
                - Stable camera position
                - High-resolution video source
                """
            )

    gr.Markdown(
        """
        ---
        **Note:** Real-time processing speed depends on your hardware.
        GPU acceleration recommended for best performance.
        """
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Different port from main app
        share=False
    )
