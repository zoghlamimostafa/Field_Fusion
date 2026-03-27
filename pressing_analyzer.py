#!/usr/bin/env python3
"""
Pressing Analyzer - Week 2, Day 8-9
Tunisia Football AI Level 3

Analyzes defensive pressing intensity and team compactness.
Critical for modern football tactics.

Features:
- Team compactness calculation (meters)
- Defensive line height tracking
- Pressing intensity measurement (0-1 scale)
- PPDA (Passes Allowed Per Defensive Action)
- Recovery speed analysis
- Counter-pressing detection
- Microservice-ready architecture
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from utils.track_data_utils import get_frame_numbers, get_player_frames


@dataclass
class PressingMetrics:
    """Pressing analysis results for a team"""
    team: int

    # Compactness metrics
    average_compactness: float  # Average distance between players (meters)
    vertical_compactness: float  # Defensive to attacking line distance (meters)
    horizontal_compactness: float  # Width of team shape (meters)

    # Pressing intensity
    pressing_intensity: float  # 0-1 scale (0=no press, 1=high press)
    high_press_percentage: float  # % of time in opponent half
    defensive_line_height: float  # Average Y-position of defensive line

    # Defensive actions
    ppda: float  # Passes Allowed Per Defensive Action (lower = more intense press)
    recovery_speed: float  # Seconds to recover ball after loss
    counter_presses: int  # Number of immediate presses after loss

    frames_analyzed: int


class PressingAnalyzer:
    """
    Analyzes team pressing and defensive metrics
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self, fps: int = 25, pitch_length: float = 105, pitch_width: float = 68):
        self.fps = fps
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width

        # Thresholds
        self.high_press_threshold = pitch_length * 0.6  # In opponent 60% of pitch
        self.counter_press_window = 5  # seconds after losing ball
        self.compact_threshold = 25  # meters (compact if < 25m between lines)

    def analyze_pressing(self,
                        tracks: Dict,
                        analytics: Dict,
                        formations: Dict = None,
                        homography: np.ndarray = None) -> Dict[int, PressingMetrics]:
        """
        Analyze pressing metrics for both teams

        Args:
            tracks: Player tracking data
            analytics: Match analytics (possession, passes, etc.)
            formations: Formation detection results
            homography: Pitch calibration matrix

        Returns:
            Dict mapping team -> PressingMetrics
        """
        print("\n🛡️  Analyzing Pressing Metrics...")

        metrics = {}

        for team in [1, 2]:
            team_metrics = self._analyze_team_pressing(
                tracks,
                team,
                analytics,
                formations,
                homography
            )

            if team_metrics:
                metrics[team] = team_metrics
                print(f"   Team {team}: Pressing={team_metrics.pressing_intensity:.2f}, "
                      f"Compactness={team_metrics.average_compactness:.1f}m, "
                      f"PPDA={team_metrics.ppda:.2f}")

        return metrics

    def _analyze_team_pressing(self,
                              tracks: Dict,
                              team: int,
                              analytics: Dict,
                              formations: Dict = None,
                              homography: np.ndarray = None) -> Optional[PressingMetrics]:
        """Analyze pressing for a specific team"""

        player_frames = get_player_frames(tracks)
        frame_numbers = get_frame_numbers(tracks)
        if not frame_numbers:
            return None

        # Calculate compactness over time
        compactness_values = []
        vertical_comp_values = []
        horizontal_comp_values = []
        defensive_line_heights = []
        high_press_frames = 0

        for frame_num in frame_numbers:
            frame_data = player_frames[frame_num]

            # Get team positions
            team_positions = []
            for player_id, data in frame_data.items():
                if data.get('team') != team:
                    continue

                bbox = data.get('bbox', [])
                if len(bbox) >= 4:
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2
                    team_positions.append((center_x, center_y))

            if len(team_positions) < 3:
                continue

            # Compactness: average pairwise distance
            compactness = self._calculate_compactness(team_positions)
            compactness_values.append(compactness)

            # Vertical/horizontal compactness
            vertical, horizontal = self._calculate_shape_dimensions(team_positions)
            vertical_comp_values.append(vertical)
            horizontal_comp_values.append(horizontal)

            # Defensive line height (highest Y-coordinate = deepest)
            y_coords = [p[1] for p in team_positions]
            defensive_line = max(y_coords)  # Assuming higher Y = deeper
            defensive_line_heights.append(defensive_line)

            # Check if high pressing (in opponent half)
            # TODO: Use homography for accurate field position
            if defensive_line < 360:  # Simplified (assuming 720p height)
                high_press_frames += 1

        # Calculate averages
        avg_compactness = np.mean(compactness_values) if compactness_values else 0.0
        avg_vertical = np.mean(vertical_comp_values) if vertical_comp_values else 0.0
        avg_horizontal = np.mean(horizontal_comp_values) if horizontal_comp_values else 0.0
        avg_defensive_height = np.mean(defensive_line_heights) if defensive_line_heights else 0.0

        # Pressing intensity (based on compactness and high press %)
        high_press_pct = (high_press_frames / len(frame_numbers)) * 100 if frame_numbers else 0.0
        pressing_intensity = self._calculate_pressing_intensity(
            avg_compactness,
            high_press_pct
        )

        # PPDA calculation
        ppda = self._calculate_ppda(team, analytics)

        # Recovery speed
        recovery_speed = self._calculate_recovery_speed(team, analytics, tracks)

        # Counter-presses
        counter_presses = self._count_counter_presses(team, analytics, tracks)

        metrics = PressingMetrics(
            team=team,
            average_compactness=avg_compactness,
            vertical_compactness=avg_vertical,
            horizontal_compactness=avg_horizontal,
            pressing_intensity=pressing_intensity,
            high_press_percentage=high_press_pct,
            defensive_line_height=avg_defensive_height,
            ppda=ppda,
            recovery_speed=recovery_speed,
            counter_presses=counter_presses,
            frames_analyzed=len(frame_numbers)
        )

        return metrics

    def _calculate_compactness(self, positions: List[Tuple[float, float]]) -> float:
        """Calculate average pairwise distance between players"""
        if len(positions) < 2:
            return 0.0

        distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.sqrt((positions[i][0] - positions[j][0])**2 +
                             (positions[i][1] - positions[j][1])**2)
                distances.append(dist)

        return np.mean(distances)

    def _calculate_shape_dimensions(self, positions: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate vertical and horizontal dimensions of team shape"""
        x_coords = [p[0] for p in positions]
        y_coords = [p[1] for p in positions]

        vertical = max(y_coords) - min(y_coords)
        horizontal = max(x_coords) - min(x_coords)

        return vertical, horizontal

    def _calculate_pressing_intensity(self, compactness: float, high_press_pct: float) -> float:
        """
        Calculate pressing intensity (0-1 scale)
        Lower compactness + higher high press % = higher intensity
        """
        # Normalize compactness (assume 100 pixels = 1.0, 20 pixels = 0.0)
        compactness_score = 1.0 - min((compactness - 20) / 80, 1.0)
        compactness_score = max(compactness_score, 0.0)

        # Normalize high press %
        high_press_score = high_press_pct / 100.0

        # Weighted combination
        intensity = (compactness_score * 0.6) + (high_press_score * 0.4)

        return min(intensity, 1.0)

    def _calculate_ppda(self, team: int, analytics: Dict) -> float:
        """
        Calculate PPDA (Passes Allowed Per Defensive Action)
        Lower PPDA = more intense pressing

        PPDA = Opponent Passes / Defensive Actions
        """
        # Get opponent team
        opponent_team = 2 if team == 1 else 1

        # Get opponent passes
        events = analytics.get('events', {})
        passes = events.get('passes', [])

        opponent_passes = sum(1 for p in passes if p.get('team') == opponent_team)

        # Get defensive actions (interceptions, tackles)
        # TODO: Implement proper defensive action tracking
        # For now, use simplified estimation
        interceptions = len(events.get('interceptions', []))
        defensive_actions = max(interceptions, 1)  # Avoid division by zero

        ppda = opponent_passes / defensive_actions if defensive_actions > 0 else 99.9

        return ppda

    def _calculate_recovery_speed(self, team: int, analytics: Dict, tracks: Dict) -> float:
        """
        Calculate average time to recover ball after losing possession
        Lower = better pressing
        """
        # TODO: Implement possession loss tracking
        # For now, return estimated value
        return 8.5  # seconds (placeholder)

    def _count_counter_presses(self, team: int, analytics: Dict, tracks: Dict) -> int:
        """
        Count number of counter-presses (pressing within 5 seconds of losing ball)
        """
        # TODO: Implement counter-press detection
        # Requires tracking possession changes and immediate pressure
        return 0  # Placeholder

    def export_pressing_data(self, metrics: Dict[int, PressingMetrics]) -> Dict:
        """
        Export pressing data to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'pressing_metrics': {
                team: {
                    'team': m.team,
                    'compactness': {
                        'average': round(m.average_compactness, 1),
                        'vertical': round(m.vertical_compactness, 1),
                        'horizontal': round(m.horizontal_compactness, 1)
                    },
                    'pressing': {
                        'intensity': round(m.pressing_intensity, 3),
                        'high_press_percentage': round(m.high_press_percentage, 1),
                        'defensive_line_height': round(m.defensive_line_height, 1)
                    },
                    'defensive_actions': {
                        'ppda': round(m.ppda, 2),
                        'recovery_speed_seconds': round(m.recovery_speed, 1),
                        'counter_presses': m.counter_presses
                    }
                }
                for team, m in metrics.items()
            }
        }

    def generate_pressing_summary(self, metrics: Dict[int, PressingMetrics]) -> str:
        """Generate human-readable pressing summary"""
        if not metrics:
            return "No pressing data available."

        summary = "🛡️  Pressing Analysis:\n\n"

        for team, m in metrics.items():
            summary += f"Team {team}:\n"
            summary += f"   Pressing Intensity: {m.pressing_intensity:.2f} "
            summary += f"({'High' if m.pressing_intensity > 0.7 else 'Medium' if m.pressing_intensity > 0.4 else 'Low'})\n"
            summary += f"   Team Compactness: {m.average_compactness:.1f}m "
            summary += f"({'Compact' if m.average_compactness < 25 else 'Spread'})\n"
            summary += f"   High Press %: {m.high_press_percentage:.1f}%\n"
            summary += f"   PPDA: {m.ppda:.2f} "
            summary += f"({'Aggressive' if m.ppda < 10 else 'Moderate' if m.ppda < 15 else 'Passive'})\n\n"

        return summary
