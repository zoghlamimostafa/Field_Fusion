#!/usr/bin/env python3
"""
Fatigue Estimator - Week 1, Day 5
Priority #3 for Tunisia Football AI Level 3

Estimates player fatigue for injury prevention and substitution decisions.
Coaches LOVE this feature - prevents injuries = saves money.

Features:
- Sprint counting (> 20 km/h)
- Acceleration/deceleration tracking (> 2 m/s²)
- Intensity zone analysis (4 zones: walking/jogging/running/sprinting)
- Work rate index calculation
- Fatigue score (0-1 scale)
- Recovery time estimation
- Microservice-ready architecture
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from utils.track_data_utils import get_player_frames, iter_player_stats


@dataclass
class PlayerFatigue:
    """Player fatigue analysis results"""
    player_id: int
    team: int

    # Distance metrics
    total_distance: float
    high_intensity_distance: float  # > 15 km/h
    sprint_distance: float  # > 20 km/h

    # Intensity metrics
    sprint_count: int
    acceleration_count: int
    deceleration_count: int

    # Time in zones (seconds)
    walking_time: float  # 0-7 km/h
    jogging_time: float  # 7-15 km/h
    running_time: float  # 15-20 km/h
    sprinting_time: float  # > 20 km/h

    # Derived metrics
    work_rate_index: float  # 0-1 scale
    fatigue_score: float  # 0-1 scale (0=fresh, 1=exhausted)
    recovery_needed_minutes: int

    # Frame tracking
    frames_analyzed: int
    minutes_played: float


class FatigueEstimator:
    """
    Estimates player fatigue from tracking and speed data
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self, fps: int = 25, pitch_length: float = 105, pitch_width: float = 68):
        self.fps = fps
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width

        # Intensity zone thresholds (km/h)
        self.zones = {
            'walking': (0, 7),
            'jogging': (7, 15),
            'running': (15, 20),
            'sprinting': (20, 100)
        }

        # Sprint threshold
        self.sprint_threshold = 20.0  # km/h

        # Acceleration threshold
        self.acceleration_threshold = 2.0  # m/s²

        # Fatigue calculation weights
        self.fatigue_weights = {
            'sprint_count': 0.25,
            'high_intensity_distance': 0.20,
            'acceleration_count': 0.15,
            'sprint_frequency': 0.15,
            'work_rate': 0.15,
            'intensity_distribution': 0.10
        }

    def estimate_fatigue(self,
                        tracks: Dict,
                        analytics: Dict,
                        homography: np.ndarray = None) -> Dict[int, PlayerFatigue]:
        """
        Estimate fatigue for all players

        Args:
            tracks: Player tracking data with positions
            analytics: Speed/distance analytics
            homography: Pitch calibration matrix (for accurate distances)

        Returns:
            Dict mapping player_id -> PlayerFatigue
        """
        print("\n💪 Estimating Player Fatigue...")

        fatigue_data = {}

        for player_id, stats in iter_player_stats(analytics):
            # Extract player data
            team = stats.get('team', 1)

            # Get player trajectory
            trajectory = self._extract_player_trajectory(tracks, player_id)

            if len(trajectory) < 2:
                continue

            total_distance = stats.get('total_distance_m', stats.get('total_distance_covered', 0))
            frames = stats.get('frames_tracked', len(trajectory))
            if frames == 0:
                continue

            minutes_played = frames / (self.fps * 60)

            # Calculate speeds
            speeds = self._calculate_speeds(trajectory, self.fps)

            # Analyze intensity zones
            zone_times = self._analyze_intensity_zones(speeds, self.fps)

            # Count sprints
            sprint_count, sprint_distance = self._count_sprints(speeds, self.fps)

            # Calculate high-intensity distance
            high_intensity_distance = self._calculate_high_intensity_distance(speeds, self.fps)

            # Count accelerations/decelerations
            accel_count, decel_count = self._count_accelerations(speeds, self.fps)

            # Calculate work rate index
            work_rate = self._calculate_work_rate(speeds, zone_times, minutes_played)

            # Calculate fatigue score
            fatigue_score = self._calculate_fatigue_score(
                sprint_count=sprint_count,
                high_intensity_distance=high_intensity_distance,
                accel_count=accel_count,
                work_rate=work_rate,
                zone_times=zone_times,
                minutes_played=minutes_played
            )

            # Estimate recovery time needed
            recovery_minutes = self._estimate_recovery_time(fatigue_score, minutes_played)

            # Create fatigue object
            fatigue = PlayerFatigue(
                player_id=player_id,
                team=team,
                total_distance=total_distance,
                high_intensity_distance=high_intensity_distance,
                sprint_distance=sprint_distance,
                sprint_count=sprint_count,
                acceleration_count=accel_count,
                deceleration_count=decel_count,
                walking_time=zone_times['walking'],
                jogging_time=zone_times['jogging'],
                running_time=zone_times['running'],
                sprinting_time=zone_times['sprinting'],
                work_rate_index=work_rate,
                fatigue_score=fatigue_score,
                recovery_needed_minutes=recovery_minutes,
                frames_analyzed=frames,
                minutes_played=minutes_played
            )

            fatigue_data[player_id] = fatigue

            print(f"   Player #{player_id}: Fatigue={fatigue_score:.2f}, "
                  f"Sprints={sprint_count}, Work Rate={work_rate:.2f}")

        print(f"   ✅ Analyzed fatigue for {len(fatigue_data)} players")

        return fatigue_data

    def _extract_player_trajectory(self, tracks: Dict, player_id: int) -> List[Tuple[float, float, int]]:
        """
        Extract (x, y, frame) trajectory for a specific player
        """
        trajectory = []

        player_frames = get_player_frames(tracks)
        if not player_frames:
            return trajectory

        for frame_num in sorted(player_frames.keys()):
            frame_data = player_frames[frame_num]

            if player_id in frame_data:
                player_data = frame_data[player_id]
                position = (
                    player_data.get('field_position')
                    or player_data.get('position_adjusted')
                    or player_data.get('position')
                )
                if position and len(position) >= 2:
                    trajectory.append((float(position[0]), float(position[1]), frame_num))
                    continue

                bbox = player_data.get('bbox', [])
                if len(bbox) >= 4:
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2
                    trajectory.append((center_x, center_y, frame_num))

        return trajectory

    def _calculate_speeds(self, trajectory: List[Tuple[float, float, int]], fps: int) -> List[float]:
        """
        Calculate instantaneous speeds (km/h) from trajectory
        """
        speeds = []

        for i in range(1, len(trajectory)):
            x1, y1, frame1 = trajectory[i-1]
            x2, y2, frame2 = trajectory[i]

            # Distance in pixels
            distance_pixels = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            # Time in seconds
            time_seconds = (frame2 - frame1) / fps

            if time_seconds == 0:
                speeds.append(0)
                continue

            # Convert to meters (rough approximation: 1 pixel ≈ 0.1 meters)
            # TODO: Use homography for accurate conversion
            distance_meters = distance_pixels * 0.1

            # Speed in km/h
            speed_kmh = (distance_meters / time_seconds) * 3.6

            # Cap at reasonable maximum (40 km/h)
            speed_kmh = min(speed_kmh, 40.0)

            speeds.append(speed_kmh)

        return speeds

    def _analyze_intensity_zones(self, speeds: List[float], fps: int) -> Dict[str, float]:
        """
        Analyze time spent in each intensity zone
        Returns time in seconds for each zone
        """
        zone_frames = defaultdict(int)

        for speed in speeds:
            for zone_name, (min_speed, max_speed) in self.zones.items():
                if min_speed <= speed < max_speed:
                    zone_frames[zone_name] += 1
                    break

        # Convert frames to seconds
        zone_times = {
            zone: frames / fps
            for zone, frames in zone_frames.items()
        }

        # Ensure all zones have values
        for zone in self.zones.keys():
            if zone not in zone_times:
                zone_times[zone] = 0.0

        return zone_times

    def _count_sprints(self, speeds: List[float], fps: int) -> Tuple[int, float]:
        """
        Count number of sprints and total sprint distance
        Sprint = continuous period above sprint_threshold
        """
        sprint_count = 0
        sprint_distance = 0.0
        in_sprint = False

        for i, speed in enumerate(speeds):
            if speed >= self.sprint_threshold:
                if not in_sprint:
                    sprint_count += 1
                    in_sprint = True
                # Add sprint distance
                distance_meters = (speed / 3.6) / fps  # Convert km/h to m/frame
                sprint_distance += distance_meters
            else:
                in_sprint = False

        return sprint_count, sprint_distance

    def _calculate_high_intensity_distance(self, speeds: List[float], fps: int) -> float:
        """
        Calculate total distance covered at high intensity (> 15 km/h)
        """
        high_intensity_threshold = 15.0  # km/h
        distance = 0.0

        for speed in speeds:
            if speed >= high_intensity_threshold:
                distance_meters = (speed / 3.6) / fps  # Convert km/h to m/frame
                distance += distance_meters

        return distance

    def _count_accelerations(self, speeds: List[float], fps: int) -> Tuple[int, int]:
        """
        Count number of accelerations and decelerations
        Returns: (acceleration_count, deceleration_count)
        """
        accel_count = 0
        decel_count = 0

        for i in range(1, len(speeds)):
            speed_change = speeds[i] - speeds[i-1]
            time_seconds = 1.0 / fps

            # Acceleration in m/s²
            acceleration = (speed_change / 3.6) / time_seconds

            if acceleration > self.acceleration_threshold:
                accel_count += 1
            elif acceleration < -self.acceleration_threshold:
                decel_count += 1

        return accel_count, decel_count

    def _calculate_work_rate(self,
                            speeds: List[float],
                            zone_times: Dict[str, float],
                            minutes_played: float) -> float:
        """
        Calculate work rate index (0-1 scale)
        Higher = more intense work
        """
        if minutes_played == 0:
            return 0.0

        # Weight each zone
        zone_weights = {
            'walking': 0.1,
            'jogging': 0.3,
            'running': 0.6,
            'sprinting': 1.0
        }

        # Weighted time
        weighted_time = sum(
            zone_times.get(zone, 0) * weight
            for zone, weight in zone_weights.items()
        )

        # Normalize by total time
        total_time = minutes_played * 60  # seconds
        work_rate = weighted_time / total_time if total_time > 0 else 0.0

        return min(work_rate, 1.0)

    def _calculate_fatigue_score(self,
                                sprint_count: int,
                                high_intensity_distance: float,
                                accel_count: int,
                                work_rate: float,
                                zone_times: Dict[str, float],
                                minutes_played: float) -> float:
        """
        Calculate overall fatigue score (0-1 scale)
        0 = Fresh, 1 = Exhausted
        """
        if minutes_played == 0:
            return 0.0

        # Normalize metrics to 0-1 scale

        # 1. Sprint count normalized (20 sprints = 1.0)
        sprint_score = min(sprint_count / 20.0, 1.0)

        # 2. High-intensity distance normalized (1500m = 1.0)
        hi_distance_score = min(high_intensity_distance / 1500.0, 1.0)

        # 3. Acceleration count normalized (30 accelerations = 1.0)
        accel_score = min(accel_count / 30.0, 1.0)

        # 4. Sprint frequency (sprints per minute, 0.5 = 1.0)
        sprint_frequency = sprint_count / minutes_played
        sprint_freq_score = min(sprint_frequency / 0.5, 1.0)

        # 5. Work rate (already 0-1)
        work_rate_score = work_rate

        # 6. Intensity distribution (more sprinting = higher fatigue)
        total_time = sum(zone_times.values())
        intensity_dist_score = zone_times.get('sprinting', 0) / total_time if total_time > 0 else 0.0

        # Weighted combination
        fatigue_score = (
            self.fatigue_weights['sprint_count'] * sprint_score +
            self.fatigue_weights['high_intensity_distance'] * hi_distance_score +
            self.fatigue_weights['acceleration_count'] * accel_score +
            self.fatigue_weights['sprint_frequency'] * sprint_freq_score +
            self.fatigue_weights['work_rate'] * work_rate_score +
            self.fatigue_weights['intensity_distribution'] * intensity_dist_score
        )

        return min(fatigue_score, 1.0)

    def _estimate_recovery_time(self, fatigue_score: float, minutes_played: float) -> int:
        """
        Estimate recovery time needed (minutes)
        Based on fatigue score and duration played
        """
        # Base recovery: fatigue_score * 60 minutes
        base_recovery = fatigue_score * 60

        # Adjust for duration (longer play = more recovery)
        duration_factor = min(minutes_played / 45.0, 1.5)  # Cap at 1.5x

        recovery_minutes = int(base_recovery * duration_factor)

        return recovery_minutes

    def export_fatigue_data(self, fatigue_data: Dict[int, PlayerFatigue]) -> Dict:
        """
        Export fatigue data to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'total_players': len(fatigue_data),
            'average_fatigue': np.mean([f.fatigue_score for f in fatigue_data.values()]) if fatigue_data else 0.0,
            'high_fatigue_count': sum(1 for f in fatigue_data.values() if f.fatigue_score > 0.7),
            'players': {
                player_id: {
                    'player_id': fatigue.player_id,
                    'team': fatigue.team,
                    'distances': {
                        'total': round(fatigue.total_distance, 1),
                        'high_intensity': round(fatigue.high_intensity_distance, 1),
                        'sprint': round(fatigue.sprint_distance, 1)
                    },
                    'intensity_metrics': {
                        'sprint_count': fatigue.sprint_count,
                        'acceleration_count': fatigue.acceleration_count,
                        'deceleration_count': fatigue.deceleration_count
                    },
                    'time_in_zones': {
                        'walking': round(fatigue.walking_time, 1),
                        'jogging': round(fatigue.jogging_time, 1),
                        'running': round(fatigue.running_time, 1),
                        'sprinting': round(fatigue.sprinting_time, 1)
                    },
                    'scores': {
                        'work_rate_index': round(fatigue.work_rate_index, 3),
                        'fatigue_score': round(fatigue.fatigue_score, 3)
                    },
                    'recovery_needed_minutes': fatigue.recovery_needed_minutes,
                    'minutes_played': round(fatigue.minutes_played, 2)
                }
                for player_id, fatigue in fatigue_data.items()
            }
        }

    def generate_fatigue_summary(self, fatigue_data: Dict[int, PlayerFatigue]) -> str:
        """Generate human-readable fatigue summary"""
        if not fatigue_data:
            return "No fatigue data available."

        # Sort by fatigue score
        sorted_players = sorted(fatigue_data.values(), key=lambda f: f.fatigue_score, reverse=True)

        summary = f"💪 Fatigue Analysis ({len(fatigue_data)} players):\n\n"

        # High fatigue warnings
        high_fatigue = [f for f in sorted_players if f.fatigue_score > 0.7]
        if high_fatigue:
            summary += "⚠️  HIGH FATIGUE WARNINGS:\n"
            for fatigue in high_fatigue[:5]:  # Top 5
                summary += f"   Player #{fatigue.player_id} (Team {fatigue.team}): "
                summary += f"Fatigue={fatigue.fatigue_score:.2f}, "
                summary += f"Sprints={fatigue.sprint_count}, "
                summary += f"Recovery={fatigue.recovery_needed_minutes}min\n"
            summary += "\n"

        # Team averages
        team_fatigues = defaultdict(list)
        for fatigue in fatigue_data.values():
            team_fatigues[fatigue.team].append(fatigue.fatigue_score)

        summary += "📊 Team Averages:\n"
        for team, scores in team_fatigues.items():
            avg = np.mean(scores)
            summary += f"   Team {team}: {avg:.2f}\n"

        return summary
