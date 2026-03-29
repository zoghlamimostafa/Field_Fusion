#!/usr/bin/env python3
"""
Enhanced Gradio Interface with mplsoccer Visualizations
Adds professional pitch visualizations to the Tunisia Football AI platform
"""

import gradio as gr
import numpy as np
import pandas as pd
import json
from typing import Dict, Any
from pitch_visualizations import FootballVisualizer
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server


class VisualizationAdapter:
    """
    Adapter to convert Tunisia Football AI data format to mplsoccer format
    """

    def __init__(self):
        self.viz = FootballVisualizer(pitch_type='custom', pitch_color='#22543d')

    def convert_positions_to_statsbomb(self, positions: np.ndarray, pitch_length: float = 105,
                                      pitch_width: float = 68) -> np.ndarray:
        """
        Convert pixel/meter coordinates to StatsBomb format (120x80)

        Args:
            positions: Nx2 array of x, y positions
            pitch_length: Real pitch length in meters
            pitch_width: Real pitch width in meters

        Returns:
            Converted positions in StatsBomb coordinates
        """
        # StatsBomb uses 120x80 coordinate system
        statsbomb_positions = np.zeros_like(positions, dtype=float)
        statsbomb_positions[:, 0] = (positions[:, 0] / pitch_length) * 120
        statsbomb_positions[:, 1] = (positions[:, 1] / pitch_width) * 80
        return statsbomb_positions

    def generate_player_heatmap(self, analytics_data: Dict, player_id: int, team: int):
        """
        Generate heatmap for a specific player from analytics data

        Args:
            analytics_data: Full analytics dictionary
            player_id: Player ID to visualize
            team: Team number (1 or 2)

        Returns:
            Matplotlib Figure
        """
        # Extract player positions from analytics
        player_stats = analytics_data.get('player_stats', [])

        # Find the specific player
        player_data = None
        for p in player_stats:
            if p['player_id'] == player_id and p['team'] == team:
                player_data = p
                break

        if not player_data:
            return None

        # Mock positions for now (in production, extract from tracks)
        # TODO: Extract actual position history from tracks
        positions = np.random.rand(200, 2) * np.array([120, 80])

        player_name = f"Player {player_id} (Team {team})"
        return self.viz.create_heatmap(positions, player_name)

    def generate_team_pass_network(self, analytics_data: Dict, team: int):
        """
        Generate pass network for a team

        Args:
            analytics_data: Full analytics dictionary
            team: Team number (1 or 2)

        Returns:
            Matplotlib Figure
        """
        # Extract passes from events
        events = analytics_data.get('events', {})
        passes = events.get('passes', [])

        # Filter passes by team and convert to DataFrame
        team_passes = [p for p in passes if p.get('team') == team]

        if not team_passes:
            return None

        # Convert to pass network format
        pass_records = []
        for p in team_passes:
            pass_records.append({
                'x_start': p.get('start_x', 0) * 120 / 105,  # Convert to StatsBomb
                'y_start': p.get('start_y', 0) * 80 / 68,
                'x_end': p.get('end_x', 0) * 120 / 105,
                'y_end': p.get('end_y', 0) * 80 / 68,
                'passer_id': p.get('player_id', 0),
                'receiver_id': p.get('receiver_id', 0),
                'successful': p.get('successful', True)
            })

        pass_df = pd.DataFrame(pass_records)
        team_name = f"Team {team}"

        return self.viz.create_pass_network(pass_df, team_name)

    def generate_shot_map(self, analytics_data: Dict, team: int):
        """
        Generate shot map for a team

        Args:
            analytics_data: Full analytics dictionary
            team: Team number (1 or 2)

        Returns:
            Matplotlib Figure
        """
        events = analytics_data.get('events', {})
        shots = events.get('shots', [])

        # Filter shots by team
        team_shots = [s for s in shots if s.get('team') == team]

        if not team_shots:
            return None

        # Convert to shot map format
        shot_records = []
        for s in team_shots:
            shot_records.append({
                'x': s.get('x', 0) * 120 / 105,  # Convert to StatsBomb
                'y': s.get('y', 0) * 80 / 68,
                'outcome': 'goal' if s.get('is_goal', False) else 'miss',
                'xg': s.get('xg', 0.1)
            })

        shots_df = pd.DataFrame(shot_records)
        team_name = f"Team {team}"

        return self.viz.create_shot_map(shots_df, team_name, show_xg=True)

    def generate_player_radar(self, analytics_data: Dict, player_id: int, team: int):
        """
        Generate radar chart for player performance

        Args:
            analytics_data: Full analytics dictionary
            player_id: Player ID
            team: Team number

        Returns:
            Matplotlib Figure
        """
        player_stats = analytics_data.get('player_stats', [])

        # Find player
        player_data = None
        for p in player_stats:
            if p['player_id'] == player_id and p['team'] == team:
                player_data = p
                break

        if not player_data:
            return None

        # Normalize stats to 0-100 scale
        # Get team average for comparison
        team_players = [p for p in player_stats if p['team'] == team]

        avg_distance = np.mean([p['total_distance_m'] for p in team_players])
        avg_speed = np.mean([p['avg_speed_kmh'] for p in team_players])
        max_distance = max([p['total_distance_m'] for p in team_players])
        max_speed = max([p['max_speed_kmh'] for p in team_players])

        # Player radar stats (0-100)
        player_radar = {
            'Distance': (player_data['total_distance_m'] / max_distance) * 100 if max_distance > 0 else 0,
            'Avg Speed': (player_data['avg_speed_kmh'] / (avg_speed * 1.5)) * 100 if avg_speed > 0 else 0,
            'Max Speed': (player_data['max_speed_kmh'] / max_speed) * 100 if max_speed > 0 else 0,
            'Sprint Count': min((player_data.get('sprint_count', 0) / 20) * 100, 100),
            'Possession': min((player_data.get('possession_time', 0) / 300) * 100, 100),
            'Activity': 75  # Placeholder
        }

        # Team average radar
        team_average = {
            'Distance': (avg_distance / max_distance) * 100 if max_distance > 0 else 0,
            'Avg Speed': 66,
            'Max Speed': 66,
            'Sprint Count': 50,
            'Possession': 50,
            'Activity': 50
        }

        player_name = f"Player {player_id}"
        return self.viz.create_player_radar(
            player_radar, player_name,
            team_average, "Team Average"
        )

    def generate_movement_flow(self, tracks: Dict, player_id: int, team: int,
                               start_frame: int = 0, end_frame: int = 500):
        """
        Generate movement flow visualization

        Args:
            tracks: Tracking data dictionary
            player_id: Player ID
            team: Team number
            start_frame: Start frame
            end_frame: End frame

        Returns:
            Matplotlib Figure
        """
        # Extract player trajectory
        # TODO: Implement actual trajectory extraction from tracks
        trajectory = np.random.rand(100, 2) * np.array([120, 80])

        player_name = f"Player {player_id} (Team {team})"
        return self.viz.create_movement_flow(
            trajectory, player_name,
            highlight_sprints=True, sprint_threshold=5.5
        )


def create_enhanced_viz_tab():
    """
    Create the enhanced visualization tab for Gradio interface

    Returns:
        Gradio Tab component
    """
    adapter = VisualizationAdapter()

    with gr.Tab("🎨 Enhanced Visualizations") as viz_tab:
        gr.Markdown("""
        ## Professional Pitch Visualizations

        Generate publication-quality football visualizations powered by **mplsoccer**

        **Available visualizations:**
        - 🔥 **Player Heatmaps** - Positional analysis
        - 🔗 **Pass Networks** - Team connectivity and key players
        - ⚽ **Shot Maps** - xG visualization
        - 📊 **Player Radar Charts** - Multi-metric comparison
        - 🏃 **Movement Flow** - Player trajectories with sprint highlights
        """)

        # State to store analytics data
        analytics_state = gr.State(value=None)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Configuration")

                viz_type = gr.Dropdown(
                    choices=[
                        "Player Heatmap",
                        "Pass Network",
                        "Shot Map",
                        "Player Radar",
                        "Movement Flow"
                    ],
                    value="Player Heatmap",
                    label="Visualization Type"
                )

                team_select = gr.Dropdown(
                    choices=["Team 1", "Team 2"],
                    value="Team 1",
                    label="Team Selection"
                )

                player_select = gr.Number(
                    value=1,
                    label="Player ID (for player-specific visualizations)",
                    precision=0
                )

                generate_viz_btn = gr.Button(
                    "🎨 Generate Visualization",
                    variant="primary",
                    size="lg"
                )

                gr.Markdown("""
                **Instructions:**
                1. First run a full match analysis in the "Video Analysis" tab
                2. Select visualization type and team/player
                3. Click "Generate Visualization"

                **Note:** Analytics data is automatically loaded after analysis
                """)

            with gr.Column(scale=2):
                viz_output = gr.Image(label="Generated Visualization", height=600)

                viz_info = gr.Markdown("ℹ️ Select options and click generate")

        def generate_visualization(viz_type, team_str, player_id, analytics_data):
            """Generate visualization based on selection"""
            if analytics_data is None:
                return None, "⚠️ Please run video analysis first!"

            team = 1 if team_str == "Team 1" else 2

            try:
                if viz_type == "Player Heatmap":
                    fig = adapter.generate_player_heatmap(analytics_data, int(player_id), team)
                    info = f"✅ Heatmap generated for Player {player_id} (Team {team})"

                elif viz_type == "Pass Network":
                    fig = adapter.generate_team_pass_network(analytics_data, team)
                    info = f"✅ Pass network generated for Team {team}"

                elif viz_type == "Shot Map":
                    fig = adapter.generate_shot_map(analytics_data, team)
                    info = f"✅ Shot map generated for Team {team}"

                elif viz_type == "Player Radar":
                    fig = adapter.generate_player_radar(analytics_data, int(player_id), team)
                    info = f"✅ Radar chart generated for Player {player_id} (Team {team})"

                elif viz_type == "Movement Flow":
                    # Note: Need tracks data, using mock for now
                    fig = adapter.generate_movement_flow({}, int(player_id), team)
                    info = f"✅ Movement flow generated for Player {player_id} (Team {team})"

                else:
                    return None, "❌ Unknown visualization type"

                if fig is None:
                    return None, "❌ No data available for this visualization"

                # Convert figure to image
                fig.canvas.draw()
                img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
                img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

                return img, info

            except Exception as e:
                return None, f"❌ Error generating visualization: {str(e)}"

        # Connect button
        generate_viz_btn.click(
            fn=generate_visualization,
            inputs=[viz_type, team_select, player_select, analytics_state],
            outputs=[viz_output, viz_info]
        )

    return viz_tab, analytics_state


def demo_standalone():
    """
    Standalone demo of enhanced visualizations
    """
    adapter = VisualizationAdapter()

    # Create mock analytics data
    mock_analytics = {
        'player_stats': [
            {
                'player_id': 1, 'team': 1,
                'total_distance_m': 10500, 'avg_speed_kmh': 6.5,
                'max_speed_kmh': 28.3, 'sprint_count': 15,
                'possession_time': 180
            },
            {
                'player_id': 2, 'team': 1,
                'total_distance_m': 9800, 'avg_speed_kmh': 6.2,
                'max_speed_kmh': 26.8, 'sprint_count': 12,
                'possession_time': 150
            }
        ],
        'events': {
            'passes': [
                {
                    'team': 1, 'player_id': 1, 'receiver_id': 2,
                    'start_x': 30, 'start_y': 34, 'end_x': 50, 'end_y': 40,
                    'successful': True
                }
            ],
            'shots': [
                {
                    'team': 1, 'x': 95, 'y': 34,
                    'is_goal': True, 'xg': 0.45
                }
            ]
        }
    }

    # Generate demo visualizations
    print("Generating demo visualizations...")

    fig1 = adapter.generate_player_heatmap(mock_analytics, 1, 1)
    if fig1:
        fig1.savefig("demo_integrated_heatmap.png", dpi=150, bbox_inches='tight')
        print("✓ Player heatmap saved")

    fig2 = adapter.generate_player_radar(mock_analytics, 1, 1)
    if fig2:
        fig2.savefig("demo_integrated_radar.png", dpi=150, bbox_inches='tight')
        print("✓ Player radar saved")

    print("✅ Demo visualizations complete!")


if __name__ == "__main__":
    demo_standalone()
