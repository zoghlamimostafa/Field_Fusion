#!/usr/bin/env python3
"""
Space Control Analyzer - Phase 2, Task 3
Tunisia Football AI Advanced Physical Analytics

Implements Voronoi-based territorial dominance analysis for tactical insights.

Features:
- Voronoi tessellation of pitch based on player positions
- Team space control percentage
- Zonal control (defensive/middle/attacking thirds)
- Pressure analysis and opponent density
- Space control evolution over time
- Dominant zones identification

References:
- Laurie Shaw's "Friends of Tracking" tutorial series
- Fernandez & Bornn (2018): "Wide Open Spaces" - pitch control model
"""

import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
from scipy.spatial import distance
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


@dataclass
class SpaceControlMetrics:
    """Results from space control analysis"""
    frame_num: int

    # Overall control
    team_1_control_percent: float
    team_2_control_percent: float

    # Zonal control (thirds)
    defensive_third_control: Dict[int, float]  # team_id -> percentage
    middle_third_control: Dict[int, float]
    attacking_third_control: Dict[int, float]

    # Dominant zones
    team_1_dominant_zones: int  # Number of Voronoi cells
    team_2_dominant_zones: int

    # Pressure metrics
    average_opponent_distance: Dict[int, float]  # team_id -> avg distance to nearest opponent
    high_pressure_zones: int  # Zones with <5m to opponent

    # Player-specific
    player_control_areas: Dict[int, float]  # player_id -> area in m²


@dataclass
class TeamSpaceControlSummary:
    """Summary of space control over multiple frames"""
    team_id: int

    # Average control
    avg_total_control: float
    avg_defensive_third: float
    avg_middle_third: float
    avg_attacking_third: float

    # Variability
    control_std_dev: float

    # Dominance metrics
    frames_with_majority: int  # Frames where team had >50% control
    total_frames: int

    # Pressure
    avg_pressure_received: float  # Average opponent distance
    high_pressure_count: int  # Count of high pressure situations


class SpaceControlAnalyzer:
    """
    Analyze territorial control using Voronoi tessellation

    The Voronoi diagram divides the pitch into cells, where each cell
    contains all points closer to one player than to any other player.
    The area of cells controlled by each team indicates territorial dominance.
    """

    def __init__(self, pitch_length: float = 105.0, pitch_width: float = 68.0):
        """
        Initialize space control analyzer

        Args:
            pitch_length: Length of pitch in meters (default: 105m)
            pitch_width: Width of pitch in meters (default: 68m)
        """
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width

        # Define pitch boundaries
        self.pitch_bounds = {
            'x_min': 0.0,
            'x_max': pitch_length,
            'y_min': 0.0,
            'y_max': pitch_width
        }

        # Define pitch thirds (for zonal analysis)
        self.defensive_third = (0.0, pitch_length / 3)
        self.middle_third = (pitch_length / 3, 2 * pitch_length / 3)
        self.attacking_third = (2 * pitch_length / 3, pitch_length)

        # High pressure threshold (meters)
        self.high_pressure_threshold = 5.0

    def calculate_voronoi(self,
                         player_positions: Dict[int, Tuple[float, float, int]]
                         ) -> Tuple[Voronoi, Dict[int, int]]:
        """
        Calculate Voronoi diagram for player positions

        Args:
            player_positions: Dict mapping player_id -> (x, y, team_id)

        Returns:
            Tuple of (Voronoi object, dict mapping point_index -> team_id)
        """
        if len(player_positions) < 4:
            # Need at least 4 points for meaningful Voronoi
            return None, {}

        # Extract positions and team mappings
        points = []
        player_ids = []
        teams = {}

        for idx, (player_id, (x, y, team)) in enumerate(player_positions.items()):
            # Ensure position is within bounds
            x = np.clip(x, self.pitch_bounds['x_min'], self.pitch_bounds['x_max'])
            y = np.clip(y, self.pitch_bounds['y_min'], self.pitch_bounds['y_max'])

            points.append([x, y])
            player_ids.append(player_id)
            teams[idx] = team

        points = np.array(points)

        # Add boundary points to ensure proper tessellation at edges
        # This prevents infinite regions
        boundary_points = self._create_boundary_points()
        all_points = np.vstack([points, boundary_points])

        # Create Voronoi diagram
        vor = Voronoi(all_points)

        # Map only original points to teams (not boundary points)
        team_mapping = {i: teams[i] for i in range(len(points))}

        return vor, team_mapping

    def _create_boundary_points(self) -> np.ndarray:
        """Create boundary points around pitch to bound Voronoi regions"""
        margin = 10.0  # meters outside pitch
        boundary_points = []

        # Create a grid of points around the pitch
        x_coords = [
            self.pitch_bounds['x_min'] - margin,
            self.pitch_bounds['x_max'] + margin
        ]
        y_coords = [
            self.pitch_bounds['y_min'] - margin,
            self.pitch_bounds['y_max'] + margin
        ]

        # Add corner and edge points
        for x in np.linspace(x_coords[0], x_coords[1], 10):
            boundary_points.append([x, y_coords[0]])  # Bottom edge
            boundary_points.append([x, y_coords[1]])  # Top edge

        for y in np.linspace(y_coords[0], y_coords[1], 7):
            boundary_points.append([x_coords[0], y])  # Left edge
            boundary_points.append([x_coords[1], y])  # Right edge

        return np.array(boundary_points)

    def calculate_space_control(self,
                                player_positions: Dict[int, Tuple[float, float, int]],
                                frame_num: int = 0
                                ) -> Optional[SpaceControlMetrics]:
        """
        Calculate space control metrics for a single frame

        Args:
            player_positions: Dict mapping player_id -> (x, y, team_id)
            frame_num: Frame number for tracking

        Returns:
            SpaceControlMetrics object or None if insufficient data
        """
        if len(player_positions) < 4:
            return None

        # Calculate Voronoi diagram
        vor, team_mapping = self.calculate_voronoi(player_positions)

        if vor is None:
            return None

        # Calculate areas for each cell
        cell_areas = {}
        player_list = list(player_positions.keys())

        for point_idx, team_id in team_mapping.items():
            region_idx = vor.point_region[point_idx]
            region = vor.regions[region_idx]

            # Skip infinite regions and empty regions
            if -1 in region or len(region) == 0:
                continue

            # Get vertices of this region
            vertices = [vor.vertices[i] for i in region]

            # Calculate area of polygon (only within pitch bounds)
            area = self._calculate_clipped_area(vertices)

            if area > 0:
                player_id = player_list[point_idx] if point_idx < len(player_list) else -1
                if player_id != -1:
                    cell_areas[player_id] = {
                        'area': area,
                        'team': team_id,
                        'vertices': vertices
                    }

        # Calculate team control percentages
        team_areas = defaultdict(float)
        for player_id, data in cell_areas.items():
            team_areas[data['team']] += data['area']

        total_area = sum(team_areas.values())

        if total_area == 0:
            return None

        team_control = {
            team: (area / total_area) * 100
            for team, area in team_areas.items()
        }

        # Calculate zonal control (thirds)
        zonal_control = self._calculate_zonal_control(cell_areas)

        # Calculate pressure metrics
        pressure_metrics = self._calculate_pressure_metrics(player_positions)

        # Count dominant zones
        team_zones = defaultdict(int)
        for data in cell_areas.values():
            team_zones[data['team']] += 1

        # Create metrics object
        metrics = SpaceControlMetrics(
            frame_num=frame_num,
            team_1_control_percent=team_control.get(1, 0.0),
            team_2_control_percent=team_control.get(2, 0.0),
            defensive_third_control=zonal_control['defensive'],
            middle_third_control=zonal_control['middle'],
            attacking_third_control=zonal_control['attacking'],
            team_1_dominant_zones=team_zones.get(1, 0),
            team_2_dominant_zones=team_zones.get(2, 0),
            average_opponent_distance=pressure_metrics['avg_opponent_distance'],
            high_pressure_zones=pressure_metrics['high_pressure_count'],
            player_control_areas={
                player_id: data['area']
                for player_id, data in cell_areas.items()
            }
        )

        return metrics

    def _calculate_clipped_area(self, vertices: List) -> float:
        """
        Calculate area of polygon clipped to pitch boundaries

        Args:
            vertices: List of (x, y) vertex coordinates

        Returns:
            Area in square meters
        """
        if len(vertices) < 3:
            return 0.0

        # Clip vertices to pitch bounds
        clipped_vertices = []
        for x, y in vertices:
            x_clipped = np.clip(x, self.pitch_bounds['x_min'], self.pitch_bounds['x_max'])
            y_clipped = np.clip(y, self.pitch_bounds['y_min'], self.pitch_bounds['y_max'])
            clipped_vertices.append([x_clipped, y_clipped])

        # Calculate area using shoelace formula
        vertices_array = np.array(clipped_vertices)

        # Ensure vertices form a closed polygon
        if not np.array_equal(vertices_array[0], vertices_array[-1]):
            vertices_array = np.vstack([vertices_array, vertices_array[0]])

        # Shoelace formula
        x = vertices_array[:, 0]
        y = vertices_array[:, 1]
        area = 0.5 * np.abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))

        # Ensure area doesn't exceed pitch area
        max_area = self.pitch_length * self.pitch_width
        area = min(area, max_area)

        return area

    def _calculate_zonal_control(self, cell_areas: Dict) -> Dict:
        """Calculate control percentage for each third of the pitch"""
        zonal_areas = {
            'defensive': defaultdict(float),
            'middle': defaultdict(float),
            'attacking': defaultdict(float)
        }

        for player_id, data in cell_areas.items():
            vertices = data['vertices']
            team = data['team']

            # Determine which zone(s) this cell occupies
            # Use centroid for simplicity
            centroid_x = np.mean([v[0] for v in vertices])

            if self.defensive_third[0] <= centroid_x < self.defensive_third[1]:
                zonal_areas['defensive'][team] += data['area']
            elif self.middle_third[0] <= centroid_x < self.middle_third[1]:
                zonal_areas['middle'][team] += data['area']
            elif self.attacking_third[0] <= centroid_x <= self.attacking_third[1]:
                zonal_areas['attacking'][team] += data['area']

        # Convert to percentages
        zonal_control = {}
        for zone, areas in zonal_areas.items():
            total = sum(areas.values())
            if total > 0:
                zonal_control[zone] = {
                    team: (area / total) * 100
                    for team, area in areas.items()
                }
            else:
                zonal_control[zone] = {1: 0.0, 2: 0.0}

        return zonal_control

    def _calculate_pressure_metrics(self,
                                   player_positions: Dict[int, Tuple[float, float, int]]
                                   ) -> Dict:
        """Calculate pressure metrics based on proximity to opponents"""
        team_players = defaultdict(list)

        # Group players by team
        for player_id, (x, y, team) in player_positions.items():
            team_players[team].append((player_id, x, y))

        # Calculate average distance to nearest opponent for each team
        avg_distances = {}
        high_pressure_count = 0

        for team, players in team_players.items():
            opponent_team = 3 - team  # Switch between 1 and 2
            if opponent_team not in team_players:
                avg_distances[team] = float('inf')
                continue

            opponents = team_players[opponent_team]
            distances = []

            for player_id, px, py in players:
                # Find nearest opponent
                min_dist = float('inf')
                for _, ox, oy in opponents:
                    dist = np.sqrt((px - ox)**2 + (py - oy)**2)
                    min_dist = min(min_dist, dist)

                distances.append(min_dist)

                # Count high pressure situations
                if min_dist < self.high_pressure_threshold:
                    high_pressure_count += 1

            avg_distances[team] = np.mean(distances) if distances else float('inf')

        return {
            'avg_opponent_distance': avg_distances,
            'high_pressure_count': high_pressure_count
        }

    def analyze_sequence(self,
                        frame_data: Dict[int, Dict[int, Tuple[float, float, int]]]
                        ) -> List[SpaceControlMetrics]:
        """
        Analyze space control over multiple frames

        Args:
            frame_data: Dict mapping frame_num -> player_positions

        Returns:
            List of SpaceControlMetrics for each frame
        """
        metrics_list = []

        for frame_num in sorted(frame_data.keys()):
            player_positions = frame_data[frame_num]
            metrics = self.calculate_space_control(player_positions, frame_num)

            if metrics:
                metrics_list.append(metrics)

        return metrics_list

    def summarize_team_control(self,
                               metrics_list: List[SpaceControlMetrics],
                               team_id: int
                               ) -> TeamSpaceControlSummary:
        """
        Summarize space control for a team over multiple frames

        Args:
            metrics_list: List of SpaceControlMetrics
            team_id: Team to summarize

        Returns:
            TeamSpaceControlSummary object
        """
        if not metrics_list:
            return self._empty_summary(team_id)

        # Extract team-specific data
        if team_id == 1:
            total_controls = [m.team_1_control_percent for m in metrics_list]
        else:
            total_controls = [m.team_2_control_percent for m in metrics_list]

        defensive_controls = [
            m.defensive_third_control.get(team_id, 0.0) for m in metrics_list
        ]
        middle_controls = [
            m.middle_third_control.get(team_id, 0.0) for m in metrics_list
        ]
        attacking_controls = [
            m.attacking_third_control.get(team_id, 0.0) for m in metrics_list
        ]

        # Calculate averages
        avg_total = np.mean(total_controls)
        avg_defensive = np.mean(defensive_controls)
        avg_middle = np.mean(middle_controls)
        avg_attacking = np.mean(attacking_controls)

        # Variability
        std_dev = np.std(total_controls)

        # Dominance
        frames_majority = sum(1 for c in total_controls if c > 50.0)

        # Pressure
        pressure_values = [
            m.average_opponent_distance.get(team_id, float('inf'))
            for m in metrics_list
        ]
        avg_pressure = np.mean([p for p in pressure_values if p != float('inf')])
        high_pressure = sum(m.high_pressure_zones for m in metrics_list)

        return TeamSpaceControlSummary(
            team_id=team_id,
            avg_total_control=avg_total,
            avg_defensive_third=avg_defensive,
            avg_middle_third=avg_middle,
            avg_attacking_third=avg_attacking,
            control_std_dev=std_dev,
            frames_with_majority=frames_majority,
            total_frames=len(metrics_list),
            avg_pressure_received=avg_pressure if not np.isnan(avg_pressure) else 0.0,
            high_pressure_count=high_pressure
        )

    def _empty_summary(self, team_id: int) -> TeamSpaceControlSummary:
        """Return empty summary for team with no data"""
        return TeamSpaceControlSummary(
            team_id=team_id,
            avg_total_control=0.0,
            avg_defensive_third=0.0,
            avg_middle_third=0.0,
            avg_attacking_third=0.0,
            control_std_dev=0.0,
            frames_with_majority=0,
            total_frames=0,
            avg_pressure_received=0.0,
            high_pressure_count=0
        )

    def export_metrics(self, metrics: SpaceControlMetrics) -> Dict:
        """Export metrics to dictionary format for JSON/API"""
        return {
            'frame': metrics.frame_num,
            'team_control': {
                'team_1': round(metrics.team_1_control_percent, 2),
                'team_2': round(metrics.team_2_control_percent, 2)
            },
            'zonal_control': {
                'defensive_third': {
                    team: round(pct, 2)
                    for team, pct in metrics.defensive_third_control.items()
                },
                'middle_third': {
                    team: round(pct, 2)
                    for team, pct in metrics.middle_third_control.items()
                },
                'attacking_third': {
                    team: round(pct, 2)
                    for team, pct in metrics.attacking_third_control.items()
                }
            },
            'dominant_zones': {
                'team_1': metrics.team_1_dominant_zones,
                'team_2': metrics.team_2_dominant_zones
            },
            'pressure': {
                'avg_opponent_distance': {
                    team: round(dist, 2)
                    for team, dist in metrics.average_opponent_distance.items()
                },
                'high_pressure_zones': metrics.high_pressure_zones
            },
            'player_areas_m2': {
                player_id: round(area, 2)
                for player_id, area in metrics.player_control_areas.items()
            }
        }


if __name__ == "__main__":
    """Demo: Calculate space control for sample match scenario"""
    print("=" * 60)
    print("Space Control Analyzer Demo")
    print("=" * 60)

    # Create analyzer
    analyzer = SpaceControlAnalyzer(pitch_length=105.0, pitch_width=68.0)

    # Simulate player positions (11v11)
    print("\nSimulating 11v11 match scenario...")

    # Team 1 (defensive formation)
    team1_positions = {
        1: (10, 34, 1),   # GK
        2: (25, 10, 1),   # RB
        3: (25, 30, 1),   # CB
        4: (25, 40, 1),   # CB
        5: (25, 60, 1),   # LB
        6: (45, 25, 1),   # CM
        7: (45, 45, 1),   # CM
        8: (60, 20, 1),   # RM
        9: (60, 50, 1),   # LM
        10: (75, 30, 1),  # FW
        11: (75, 40, 1),  # FW
    }

    # Team 2 (attacking formation)
    team2_positions = {
        12: (95, 34, 2),  # GK
        13: (80, 12, 2),  # RB
        14: (80, 28, 2),  # CB
        15: (80, 42, 2),  # CB
        16: (80, 58, 2),  # LB
        17: (60, 34, 2),  # CM
        18: (50, 20, 2),  # RM
        19: (50, 48, 2),  # LM
        20: (35, 25, 2),  # FW
        21: (35, 35, 2),  # FW
        22: (35, 45, 2),  # FW
    }

    all_positions = {**team1_positions, **team2_positions}

    # Calculate space control
    print("Calculating Voronoi tessellation and space control...")
    metrics = analyzer.calculate_space_control(all_positions, frame_num=1)

    if metrics:
        print(f"\n{'Space Control Results':^60}")
        print("=" * 60)
        print(f"Team 1 Control: {metrics.team_1_control_percent:.1f}%")
        print(f"Team 2 Control: {metrics.team_2_control_percent:.1f}%")
        print()
        print("Zonal Control (Thirds):")
        print(f"  Defensive Third:")
        for team, pct in metrics.defensive_third_control.items():
            print(f"    Team {team}: {pct:.1f}%")
        print(f"  Middle Third:")
        for team, pct in metrics.middle_third_control.items():
            print(f"    Team {team}: {pct:.1f}%")
        print(f"  Attacking Third:")
        for team, pct in metrics.attacking_third_control.items():
            print(f"    Team {team}: {pct:.1f}%")
        print()
        print(f"Team 1 Dominant Zones: {metrics.team_1_dominant_zones}")
        print(f"Team 2 Dominant Zones: {metrics.team_2_dominant_zones}")
        print(f"High Pressure Zones: {metrics.high_pressure_zones}")

        # Export example
        print("\n" + "=" * 60)
        print("JSON Export Sample:")
        print("=" * 60)
        import json
        exported = analyzer.export_metrics(metrics)
        print(json.dumps(exported, indent=2))

    print("\n✅ Space control analysis complete!")
