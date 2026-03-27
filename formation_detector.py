#!/usr/bin/env python3
"""
Formation Detector - Week 1, Day 6-7
Priority #4 for Tunisia Football AI Level 3

Detects team formations (4-4-2, 4-3-3, 3-5-2, etc.) and tactical shape.
Coaches use this to understand opponent tactics and verify their own team's structure.

Features:
- Line clustering (defensive/midfield/attacking lines)
- Formation matching (8 common formations)
- Shape analysis (width, depth, compactness)
- Tactical state classification (attacking/defending/transition)
- Formation confidence scoring
- Microservice-ready architecture
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
from utils.track_data_utils import get_frame_numbers, get_player_frames


@dataclass
class Formation:
    """Team formation analysis results"""
    team: int
    formation_name: str  # e.g., "4-4-2", "4-3-3"
    confidence: float  # 0-1 scale

    # Line structure
    defenders: List[int]  # Player IDs
    midfielders: List[int]
    forwards: List[int]

    # Shape metrics
    team_width: float  # meters
    team_depth: float  # meters
    team_compactness: float  # 0-1 scale (compact to spread)

    # Tactical state
    tactical_state: str  # "attacking", "defending", "balanced", "transition"

    # Position data
    average_defensive_line: float  # Y-coordinate
    average_midfield_line: float
    average_attacking_line: float

    frames_analyzed: int


class FormationDetector:
    """
    Detects team formations using clustering and pattern matching
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self, fps: int = 25):
        self.fps = fps

        # Common formations (defenders-midfielders-forwards)
        self.known_formations = {
            '4-4-2': {'defenders': 4, 'midfielders': 4, 'forwards': 2},
            '4-3-3': {'defenders': 4, 'midfielders': 3, 'forwards': 3},
            '4-2-3-1': {'defenders': 4, 'midfielders': 5, 'forwards': 1},  # 2 DM, 3 AM
            '3-5-2': {'defenders': 3, 'midfielders': 5, 'forwards': 2},
            '4-5-1': {'defenders': 4, 'midfielders': 5, 'forwards': 1},
            '3-4-3': {'defenders': 3, 'midfielders': 4, 'forwards': 3},
            '5-3-2': {'defenders': 5, 'midfielders': 3, 'forwards': 2},
            '5-4-1': {'defenders': 5, 'midfielders': 4, 'forwards': 1}
        }

        # Clustering parameters
        self.min_players_for_formation = 8  # Need at least 8 field players
        self.line_separation_threshold = 15  # meters between lines

    def detect_formations(self,
                         tracks: Dict,
                         homography: np.ndarray = None,
                         sample_frames: int = 10) -> Dict[int, Formation]:
        """
        Detect formations for both teams

        Args:
            tracks: Player tracking data
            homography: Pitch calibration matrix (for accurate positions)
            sample_frames: Number of frames to sample across video

        Returns:
            Dict mapping team -> Formation
        """
        print("\n⚽ Detecting Team Formations...")

        formations = {}
        player_frames = get_player_frames(tracks)

        # Sample frames evenly across video
        frame_numbers = get_frame_numbers(tracks)
        if not frame_numbers:
            return formations

        sample_interval = max(len(frame_numbers) // sample_frames, 1)
        sampled_frames = frame_numbers[::sample_interval][:sample_frames]

        # Detect formation for each team
        for team in [1, 2]:
            formation = self._detect_team_formation(
                player_frames,
                team,
                sampled_frames,
                homography
            )

            if formation:
                formations[team] = formation
                print(f"   Team {team}: {formation.formation_name} "
                      f"(confidence={formation.confidence:.2f}, "
                      f"compactness={formation.team_compactness:.2f})")

        return formations

    def _detect_team_formation(self,
                              player_frames: Dict[int, Dict],
                              team: int,
                              sampled_frames: List[int],
                              homography: np.ndarray = None) -> Optional[Formation]:
        """
        Detect formation for a specific team
        """
        # Collect player positions across sampled frames
        all_positions = []  # [(player_id, x, y, frame)]

        for frame_num in sampled_frames:
            frame_data = player_frames.get(frame_num, {})

            for player_id, data in frame_data.items():
                if data.get('team') != team:
                    continue

                position = (
                    data.get('field_position')
                    or data.get('position_adjusted')
                    or data.get('position')
                )
                if position and len(position) >= 2:
                    center_x, center_y = position[:2]
                else:
                    bbox = data.get('bbox', [])
                    if len(bbox) < 4:
                        continue
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2

                # Transform to real-world if homography available
                if homography is not None and not position:
                    try:
                        pos = np.array([[[center_x, center_y]]], dtype=np.float32)
                        world_pos = cv2.perspectiveTransform(pos, homography)[0][0]
                        center_x, center_y = world_pos
                    except:
                        pass  # Use image coordinates if transformation fails

                all_positions.append((player_id, center_x, center_y, frame_num))

        if len(all_positions) < self.min_players_for_formation:
            return None

        # Average positions per player
        player_avg_positions = self._average_player_positions(all_positions)

        if len(player_avg_positions) < self.min_players_for_formation:
            return None

        # Cluster into lines (defensive, midfield, attacking)
        lines = self._cluster_into_lines(player_avg_positions)

        # Match to known formation
        formation_name, confidence = self._match_formation(lines)

        # Calculate shape metrics
        width, depth, compactness = self._calculate_shape_metrics(player_avg_positions)

        # Determine tactical state
        tactical_state = self._determine_tactical_state(player_avg_positions, team)

        # Build formation object
        formation = Formation(
            team=team,
            formation_name=formation_name,
            confidence=confidence,
            defenders=lines.get('defenders', []),
            midfielders=lines.get('midfielders', []),
            forwards=lines.get('forwards', []),
            team_width=width,
            team_depth=depth,
            team_compactness=compactness,
            tactical_state=tactical_state,
            average_defensive_line=self._get_line_avg_y(lines.get('defenders', []), player_avg_positions),
            average_midfield_line=self._get_line_avg_y(lines.get('midfielders', []), player_avg_positions),
            average_attacking_line=self._get_line_avg_y(lines.get('forwards', []), player_avg_positions),
            frames_analyzed=len(sampled_frames)
        )

        return formation

    def _average_player_positions(self,
                                  positions: List[Tuple[int, float, float, int]]) -> Dict[int, Tuple[float, float]]:
        """
        Average positions for each player across frames
        Returns: {player_id: (avg_x, avg_y)}
        """
        player_positions = defaultdict(list)

        for player_id, x, y, frame in positions:
            player_positions[player_id].append((x, y))

        avg_positions = {}
        for player_id, pos_list in player_positions.items():
            avg_x = np.mean([p[0] for p in pos_list])
            avg_y = np.mean([p[1] for p in pos_list])
            avg_positions[player_id] = (avg_x, avg_y)

        return avg_positions

    def _cluster_into_lines(self,
                           player_positions: Dict[int, Tuple[float, float]]) -> Dict[str, List[int]]:
        """
        Cluster players into defensive, midfield, and attacking lines
        Uses Y-coordinate clustering
        """
        if len(player_positions) < 3:
            return {}

        # Extract Y-coordinates (vertical position on pitch)
        player_ids = list(player_positions.keys())
        y_coords = np.array([[player_positions[pid][1]] for pid in player_ids])

        # Determine number of lines (try 3, then 2, then 4)
        best_lines = None
        best_score = -1

        for n_lines in [3, 2, 4]:
            if n_lines > len(player_ids):
                continue

            try:
                kmeans = KMeans(n_clusters=n_lines, random_state=42, n_init=10)
                labels = kmeans.fit_predict(y_coords)

                # Score based on cluster separation
                score = kmeans.inertia_

                if best_lines is None or score < best_score:
                    best_lines = labels
                    best_score = score
                    best_n_lines = n_lines
            except:
                continue

        if best_lines is None:
            return {}

        # Assign lines to roles (based on Y-coordinate)
        lines = defaultdict(list)
        line_centers = {}

        for line_id in range(best_n_lines):
            line_players = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == line_id]
            line_y = np.mean([player_positions[pid][1] for pid in line_players])
            line_centers[line_id] = line_y

        # Sort lines by Y-coordinate (top to bottom)
        sorted_lines = sorted(line_centers.items(), key=lambda x: x[1])

        if best_n_lines == 3:
            # Defenders (top), Midfielders (middle), Forwards (bottom)
            lines['defenders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[0][0]]
            lines['midfielders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[1][0]]
            lines['forwards'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[2][0]]

        elif best_n_lines == 2:
            # Defenders + Midfielders, Forwards
            lines['defenders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[0][0]][:4]
            lines['midfielders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[0][0]][4:]
            lines['forwards'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[1][0]]

        elif best_n_lines == 4:
            # Merge middle two into midfield
            lines['defenders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[0][0]]
            lines['midfielders'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] in [sorted_lines[1][0], sorted_lines[2][0]]]
            lines['forwards'] = [player_ids[i] for i in range(len(player_ids)) if best_lines[i] == sorted_lines[3][0]]

        return lines

    def _match_formation(self, lines: Dict[str, List[int]]) -> Tuple[str, float]:
        """
        Match detected lines to known formation
        Returns: (formation_name, confidence)
        """
        n_defenders = len(lines.get('defenders', []))
        n_midfielders = len(lines.get('midfielders', []))
        n_forwards = len(lines.get('forwards', []))

        # Try exact match first
        for formation_name, structure in self.known_formations.items():
            if (structure['defenders'] == n_defenders and
                structure['midfielders'] == n_midfielders and
                structure['forwards'] == n_forwards):
                return formation_name, 0.95

        # Try approximate match (allow ±1 player per line)
        best_match = None
        best_diff = float('inf')

        for formation_name, structure in self.known_formations.items():
            diff = (abs(structure['defenders'] - n_defenders) +
                   abs(structure['midfielders'] - n_midfielders) +
                   abs(structure['forwards'] - n_forwards))

            if diff < best_diff:
                best_diff = diff
                best_match = formation_name

        if best_match and best_diff <= 2:
            confidence = 0.8 - (best_diff * 0.1)  # Reduce confidence for each difference
            return best_match, confidence

        # Unknown formation
        formation_str = f"{n_defenders}-{n_midfielders}-{n_forwards}"
        return formation_str, 0.5

    def _calculate_shape_metrics(self,
                                 player_positions: Dict[int, Tuple[float, float]]) -> Tuple[float, float, float]:
        """
        Calculate team shape metrics
        Returns: (width, depth, compactness)
        """
        positions = list(player_positions.values())

        if len(positions) < 2:
            return 0.0, 0.0, 0.0

        x_coords = [p[0] for p in positions]
        y_coords = [p[1] for p in positions]

        # Width: horizontal spread
        width = max(x_coords) - min(x_coords)

        # Depth: vertical spread
        depth = max(y_coords) - min(y_coords)

        # Compactness: average distance to centroid (0-1 scale, lower = more compact)
        centroid_x = np.mean(x_coords)
        centroid_y = np.mean(y_coords)

        distances = [np.sqrt((x - centroid_x)**2 + (y - centroid_y)**2) for x, y in positions]
        avg_distance = np.mean(distances)

        # Normalize compactness (assume max distance is 50m)
        compactness = min(avg_distance / 50.0, 1.0)

        return width, depth, compactness

    def _determine_tactical_state(self,
                                  player_positions: Dict[int, Tuple[float, float]],
                                  team: int) -> str:
        """
        Determine tactical state: attacking, defending, balanced, transition
        """
        if len(player_positions) < 3:
            return "unknown"

        y_coords = [p[1] for p in player_positions.values()]
        avg_y = np.mean(y_coords)

        # Assume camera viewing from top
        # Lower Y = attacking (towards opponent goal)
        # Higher Y = defending (near own goal)

        # Simplified classification
        if avg_y < 300:
            return "attacking"
        elif avg_y > 500:
            return "defending"
        else:
            return "balanced"

    def _get_line_avg_y(self, player_ids: List[int], positions: Dict[int, Tuple[float, float]]) -> float:
        """Get average Y-coordinate for a line of players"""
        if not player_ids:
            return 0.0

        y_coords = [positions[pid][1] for pid in player_ids if pid in positions]
        return np.mean(y_coords) if y_coords else 0.0

    def export_formations(self, formations: Dict[int, Formation]) -> Dict:
        """
        Export formations to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'formations': {
                team: {
                    'team': formation.team,
                    'formation_name': formation.formation_name,
                    'confidence': round(formation.confidence, 3),
                    'lines': {
                        'defenders': formation.defenders,
                        'midfielders': formation.midfielders,
                        'forwards': formation.forwards
                    },
                    'shape': {
                        'width': round(formation.team_width, 1),
                        'depth': round(formation.team_depth, 1),
                        'compactness': round(formation.team_compactness, 3)
                    },
                    'tactical_state': formation.tactical_state,
                    'line_positions': {
                        'defensive_line': round(formation.average_defensive_line, 1),
                        'midfield_line': round(formation.average_midfield_line, 1),
                        'attacking_line': round(formation.average_attacking_line, 1)
                    }
                }
                for team, formation in formations.items()
            }
        }

    def generate_formation_summary(self, formations: Dict[int, Formation]) -> str:
        """Generate human-readable formation summary"""
        if not formations:
            return "No formation data available."

        summary = "⚽ Formation Analysis:\n\n"

        for team, formation in formations.items():
            summary += f"Team {team}: {formation.formation_name} "
            summary += f"(confidence={formation.confidence:.2f})\n"
            summary += f"   Defenders: {len(formation.defenders)}, "
            summary += f"Midfielders: {len(formation.midfielders)}, "
            summary += f"Forwards: {len(formation.forwards)}\n"
            summary += f"   Shape: Width={formation.team_width:.1f}m, "
            summary += f"Depth={formation.team_depth:.1f}m, "
            summary += f"Compactness={formation.team_compactness:.2f}\n"
            summary += f"   Tactical State: {formation.tactical_state}\n\n"

        return summary
