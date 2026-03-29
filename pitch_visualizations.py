"""
Pitch Visualizations Module using mplsoccer
Provides professional football pitch visualizations for the Tunisia Football AI system.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mplsoccer import Pitch, VerticalPitch, Radar
from typing import List, Dict, Tuple, Optional
import pandas as pd


class FootballVisualizer:
    """
    Professional football pitch visualizations using mplsoccer library.
    Supports heatmaps, pass networks, shot maps, and player comparison radars.
    """

    def __init__(self, pitch_type: str = 'statsbomb', pitch_color: str = '#22543d'):
        """
        Initialize the visualizer.

        Args:
            pitch_type: Type of pitch coordinates ('statsbomb', 'opta', 'tracab', etc.)
            pitch_color: Background color of the pitch
        """
        self.pitch_type = pitch_type
        self.pitch_color = pitch_color
        self.pitch_line_color = '#c7d5cc'

    def create_heatmap(
        self,
        positions: np.ndarray,
        player_name: str = "Player",
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 8)
    ) -> Figure:
        """
        Create a positional heatmap for a player.

        Args:
            positions: Array of shape (N, 2) with x, y coordinates
            player_name: Name of the player
            title: Custom title (default: "{player_name} Heatmap")
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        pitch = Pitch(
            pitch_type=self.pitch_type,
            pitch_color=self.pitch_color,
            line_color=self.pitch_line_color,
            line_zorder=2
        )

        fig, ax = pitch.draw(figsize=figsize)

        # Create hexbin heatmap
        hexmap = pitch.hexbin(
            x=positions[:, 0],
            y=positions[:, 1],
            ax=ax,
            edgecolors=self.pitch_line_color,
            gridsize=20,
            cmap='hot',
            alpha=0.7
        )

        # Add colorbar
        cbar = plt.colorbar(hexmap, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Frequency', rotation=270, labelpad=20)

        # Set title
        if title is None:
            title = f"{player_name} Positional Heatmap"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    def create_pass_network(
        self,
        pass_data: pd.DataFrame,
        team_name: str = "Team",
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (14, 10)
    ) -> Figure:
        """
        Create a pass network visualization.

        Args:
            pass_data: DataFrame with columns ['x_start', 'y_start', 'x_end', 'y_end',
                      'passer_id', 'receiver_id', 'successful']
            team_name: Name of the team
            title: Custom title
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        pitch = Pitch(
            pitch_type=self.pitch_type,
            pitch_color=self.pitch_color,
            line_color=self.pitch_line_color
        )

        fig, ax = pitch.draw(figsize=figsize)

        # Calculate average positions for each player
        player_positions = {}
        for player_id in pass_data['passer_id'].unique():
            player_passes = pass_data[pass_data['passer_id'] == player_id]
            avg_x = player_passes['x_start'].mean()
            avg_y = player_passes['y_start'].mean()
            player_positions[player_id] = (avg_x, avg_y)

        # Draw passes
        for _, row in pass_data.iterrows():
            if row['passer_id'] in player_positions and row['receiver_id'] in player_positions:
                x_start, y_start = player_positions[row['passer_id']]
                x_end, y_end = player_positions[row['receiver_id']]

                color = 'green' if row['successful'] else 'red'
                alpha = 0.6 if row['successful'] else 0.3

                pitch.arrows(
                    x_start, y_start, x_end, y_end,
                    ax=ax,
                    color=color,
                    alpha=alpha,
                    width=1,
                    headwidth=3,
                    headlength=3
                )

        # Draw player nodes
        for player_id, (x, y) in player_positions.items():
            pitch.scatter(
                x, y,
                ax=ax,
                s=500,
                color='white',
                edgecolors='black',
                linewidth=2,
                zorder=3
            )

            # Add player number
            ax.text(x, y, str(player_id),
                   ha='center', va='center',
                   fontsize=10, fontweight='bold', zorder=4)

        if title is None:
            title = f"{team_name} Pass Network"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    def create_shot_map(
        self,
        shots: pd.DataFrame,
        team_name: str = "Team",
        show_xg: bool = True,
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 8)
    ) -> Figure:
        """
        Create a shot map with optional xG values.

        Args:
            shots: DataFrame with columns ['x', 'y', 'outcome', 'xg'] (xg optional)
            team_name: Name of the team
            show_xg: Whether to show xG values as marker sizes
            title: Custom title
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        pitch = Pitch(
            pitch_type=self.pitch_type,
            pitch_color=self.pitch_color,
            line_color=self.pitch_line_color,
            half=True  # Show only attacking half
        )

        fig, ax = pitch.draw(figsize=figsize)

        # Separate goals and non-goals
        goals = shots[shots['outcome'] == 'goal']
        misses = shots[shots['outcome'] != 'goal']

        # Plot misses
        if show_xg and 'xg' in misses.columns:
            sizes = misses['xg'] * 1000
        else:
            sizes = 100

        pitch.scatter(
            misses['x'], misses['y'],
            ax=ax,
            s=sizes,
            color='white',
            edgecolors='red',
            linewidth=2,
            alpha=0.7,
            label='Miss/Save'
        )

        # Plot goals
        if show_xg and 'xg' in goals.columns:
            sizes = goals['xg'] * 1000
        else:
            sizes = 200

        pitch.scatter(
            goals['x'], goals['y'],
            ax=ax,
            s=sizes,
            color='yellow',
            edgecolors='black',
            linewidth=2,
            marker='*',
            alpha=0.9,
            label='Goal',
            zorder=3
        )

        # Add legend
        ax.legend(loc='upper left', fontsize=12)

        # Calculate and display total xG
        if 'xg' in shots.columns:
            total_xg = shots['xg'].sum()
            ax.text(
                0.98, 0.02, f'Total xG: {total_xg:.2f}',
                transform=ax.transAxes,
                fontsize=12,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                ha='right', va='bottom'
            )

        if title is None:
            title = f"{team_name} Shot Map"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    def create_player_radar(
        self,
        player_stats: Dict[str, float],
        player_name: str,
        comparison_stats: Optional[Dict[str, float]] = None,
        comparison_name: str = "League Average",
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (10, 10)
    ) -> Figure:
        """
        Create a radar chart for player comparison.

        Args:
            player_stats: Dictionary of stat names to values (0-100 scale)
            player_name: Name of the player
            comparison_stats: Optional comparison stats (e.g., league average)
            comparison_name: Name for comparison data
            title: Custom title
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        params = list(player_stats.keys())
        values = list(player_stats.values())

        # Create radar chart
        radar = Radar(
            params=params,
            min_range=[0] * len(params),
            max_range=[100] * len(params),
            round_int=[False] * len(params),
            num_rings=4,
            ring_width=1,
            center_circle_radius=1
        )

        fig, ax = radar.setup_axis(figsize=figsize)

        # Plot player stats
        rings_inner = radar.draw_circles(ax=ax, facecolor='#28a745', edgecolor='#28a745')
        radar_output = radar.draw_radar(
            values, ax=ax,
            kwargs_radar={'facecolor': '#28a745', 'alpha': 0.6},
            kwargs_rings={'facecolor': '#28a745', 'alpha': 0.6}
        )

        # Plot comparison if provided
        if comparison_stats is not None:
            comparison_values = [comparison_stats.get(param, 0) for param in params]
            radar.draw_radar(
                comparison_values, ax=ax,
                kwargs_radar={'facecolor': '#dc3545', 'alpha': 0.4},
                kwargs_rings={'facecolor': '#dc3545', 'alpha': 0.4}
            )

        # Add labels
        radar_poly, rings_outer, vertices = radar_output
        radar.draw_param_labels(ax=ax, fontsize=12, fontweight='bold')

        if title is None:
            title = f"{player_name} Performance Radar"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=40)

        # Add legend
        if comparison_stats is not None:
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#28a745', alpha=0.6, label=player_name),
                Patch(facecolor='#dc3545', alpha=0.4, label=comparison_name)
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=12)

        plt.tight_layout()
        return fig

    def create_movement_flow(
        self,
        trajectory: np.ndarray,
        player_name: str = "Player",
        highlight_sprints: bool = True,
        sprint_threshold: float = 5.5,  # m/s
        title: Optional[str] = None,
        figsize: Tuple[int, int] = (14, 10)
    ) -> Figure:
        """
        Create a movement flow visualization showing player trajectory.

        Args:
            trajectory: Array of shape (N, 2) with x, y coordinates over time
            player_name: Name of the player
            highlight_sprints: Whether to highlight high-speed movements
            sprint_threshold: Speed threshold for sprint highlighting (m/s)
            title: Custom title
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        pitch = Pitch(
            pitch_type=self.pitch_type,
            pitch_color=self.pitch_color,
            line_color=self.pitch_line_color
        )

        fig, ax = pitch.draw(figsize=figsize)

        # Calculate speeds if highlighting sprints
        if highlight_sprints and len(trajectory) > 1:
            # Calculate displacement between consecutive points
            displacements = np.diff(trajectory, axis=0)
            distances = np.linalg.norm(displacements, axis=1)
            speeds = distances * 10  # Assuming 10 fps, convert to m/s

            # Plot trajectory with color based on speed
            for i in range(len(trajectory) - 1):
                color = 'red' if speeds[i] > sprint_threshold else 'blue'
                alpha = 0.8 if speeds[i] > sprint_threshold else 0.4
                linewidth = 3 if speeds[i] > sprint_threshold else 1

                pitch.lines(
                    trajectory[i, 0], trajectory[i, 1],
                    trajectory[i + 1, 0], trajectory[i + 1, 1],
                    ax=ax,
                    color=color,
                    alpha=alpha,
                    linewidth=linewidth,
                    zorder=2
                )
        else:
            # Simple trajectory line
            pitch.lines(
                trajectory[:, 0], trajectory[:, 1],
                ax=ax,
                color='blue',
                alpha=0.6,
                linewidth=2,
                zorder=2
            )

        # Mark start and end positions
        pitch.scatter(
            trajectory[0, 0], trajectory[0, 1],
            ax=ax,
            s=300,
            color='green',
            edgecolors='black',
            linewidth=2,
            marker='o',
            label='Start',
            zorder=3
        )

        pitch.scatter(
            trajectory[-1, 0], trajectory[-1, 1],
            ax=ax,
            s=300,
            color='red',
            edgecolors='black',
            linewidth=2,
            marker='X',
            label='End',
            zorder=3
        )

        ax.legend(loc='upper left', fontsize=12)

        if title is None:
            title = f"{player_name} Movement Flow"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig


def demo_visualizations():
    """
    Demonstrate all visualization types with sample data.
    """
    viz = FootballVisualizer()

    # 1. Heatmap demo
    np.random.seed(42)
    positions = np.random.rand(200, 2) * 120  # StatsBomb coordinates
    positions[:, 1] = positions[:, 1] * 0.67  # Adjust for pitch dimensions

    fig1 = viz.create_heatmap(positions, "Mohamed Salah")
    fig1.savefig("demo_heatmap.png", dpi=150, bbox_inches='tight')
    print("✓ Heatmap saved to demo_heatmap.png")

    # 2. Pass network demo
    pass_data = pd.DataFrame({
        'x_start': np.random.rand(50) * 120,
        'y_start': np.random.rand(50) * 80,
        'x_end': np.random.rand(50) * 120,
        'y_end': np.random.rand(50) * 80,
        'passer_id': np.random.randint(1, 12, 50),
        'receiver_id': np.random.randint(1, 12, 50),
        'successful': np.random.choice([True, False], 50, p=[0.8, 0.2])
    })

    fig2 = viz.create_pass_network(pass_data, "Tunisia National Team")
    fig2.savefig("demo_pass_network.png", dpi=150, bbox_inches='tight')
    print("✓ Pass network saved to demo_pass_network.png")

    # 3. Shot map demo
    shots = pd.DataFrame({
        'x': np.random.rand(20) * 20 + 100,  # Shots from attacking third
        'y': np.random.rand(20) * 80,
        'outcome': np.random.choice(['goal', 'miss', 'save'], 20, p=[0.2, 0.4, 0.4]),
        'xg': np.random.rand(20) * 0.8
    })

    fig3 = viz.create_shot_map(shots, "Tunisia National Team", show_xg=True)
    fig3.savefig("demo_shot_map.png", dpi=150, bbox_inches='tight')
    print("✓ Shot map saved to demo_shot_map.png")

    # 4. Radar chart demo
    player_stats = {
        'Speed': 85,
        'Distance': 78,
        'Passes': 92,
        'Dribbles': 88,
        'Tackles': 65,
        'Aerial': 70
    }

    comparison = {
        'Speed': 70,
        'Distance': 75,
        'Passes': 80,
        'Dribbles': 75,
        'Tackles': 70,
        'Aerial': 65
    }

    fig4 = viz.create_player_radar(player_stats, "Player #10", comparison, "Team Average")
    fig4.savefig("demo_radar.png", dpi=150, bbox_inches='tight')
    print("✓ Radar chart saved to demo_radar.png")

    print("\n✅ All demo visualizations generated successfully!")


if __name__ == "__main__":
    demo_visualizations()
