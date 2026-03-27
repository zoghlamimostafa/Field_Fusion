#!/usr/bin/env python3
"""
Alert Engine - Week 1, Day 3-4
Priority #2 for Tunisia Football AI Level 3

Detects tactical problems and generates actionable alerts for coaches.
This is the CORE of Level 3 - moving from statistics to decisions.

Features:
- 10 alert types covering all tactical scenarios
- Priority ranking (Critical/High/Medium)
- Alert suppression (max 3-5 alerts at once)
- Confidence scoring for each alert
- Microservice-ready architecture
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from utils.track_data_utils import (
    get_frame_numbers,
    get_player_frame_count,
    get_player_frames,
    iter_player_stats,
)


class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = 3  # Immediate action needed
    HIGH = 2      # Important, address soon
    MEDIUM = 1    # Monitor situation


class AlertType(Enum):
    """10 tactical alert types"""
    PLAYER_INACTIVITY = "player_inactivity"
    PLAYER_OVERLOAD = "player_overload"
    DEFENSIVE_GAP = "defensive_gap"
    FATIGUE_WARNING = "fatigue_warning"
    FORMATION_BREAK = "formation_break"
    POSSESSION_LOSS = "possession_loss"
    PRESSING_FAILURE = "pressing_failure"
    INJURY_RISK = "injury_risk"
    POSITIONAL_ERROR = "positional_error"
    TACTICAL_IMBALANCE = "tactical_imbalance"


@dataclass
class Alert:
    """Single alert instance"""
    alert_type: AlertType
    priority: AlertPriority
    player_id: Optional[int]
    team: int
    frame_range: Tuple[int, int]
    confidence: float
    title: str
    description: str
    recommendation: str
    metrics: Dict


class AlertEngine:
    """
    Generates tactical alerts from match analytics
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self,
                 fps: int = 25,
                 max_alerts_per_analysis: int = 5,
                 min_confidence: float = 0.6):
        self.fps = fps
        self.max_alerts = max_alerts_per_analysis
        self.min_confidence = min_confidence

        # Alert thresholds
        self.thresholds = {
            'inactivity_distance': 50,  # meters in 5 minutes
            'overload_distance': 8000,  # meters in 45 minutes (half)
            'overload_sprints': 25,     # sprints in 45 minutes
            'defensive_gap': 25,        # meters between defenders
            'fatigue_score': 0.75,      # 0-1 scale
            'formation_deviation': 15,  # meters from expected position
            'possession_drop': 0.3,     # 30% drop in 5 minutes
            'pressing_intensity': 0.4,  # 0-1 scale
            'injury_risk_score': 0.7,   # 0-1 scale
            'sprint_frequency': 4       # sprints per minute (dangerous)
        }

    def generate_alerts(self,
                       tracks: Dict,
                       analytics: Dict,
                       formations: Dict = None,
                       fatigue_data: Dict = None) -> List[Alert]:
        """
        Generate all alerts from match data

        Args:
            tracks: Player tracking data
            analytics: Match analytics (possession, passes, etc.)
            formations: Formation detection results
            fatigue_data: Player fatigue metrics

        Returns:
            List of prioritized alerts
        """
        alerts = []

        print("\n🚨 Generating Tactical Alerts...")

        # 1. Player inactivity alerts
        alerts.extend(self._detect_player_inactivity(tracks, analytics))

        # 2. Player overload alerts
        alerts.extend(self._detect_player_overload(tracks, analytics, fatigue_data))

        # 3. Defensive gap alerts
        alerts.extend(self._detect_defensive_gaps(tracks, formations))

        # 4. Fatigue warnings
        alerts.extend(self._detect_fatigue_warnings(fatigue_data))

        # 5. Formation break alerts
        alerts.extend(self._detect_formation_breaks(tracks, formations))

        # 6. Possession loss alerts
        alerts.extend(self._detect_possession_issues(analytics))

        # 7. Pressing failure alerts
        alerts.extend(self._detect_pressing_failures(tracks, analytics))

        # 8. Injury risk alerts
        alerts.extend(self._detect_injury_risks(fatigue_data, analytics))

        # 9. Positional error alerts
        alerts.extend(self._detect_positional_errors(tracks, formations))

        # 10. Tactical imbalance alerts
        alerts.extend(self._detect_tactical_imbalances(tracks, analytics))

        # Filter by confidence
        alerts = [a for a in alerts if a.confidence >= self.min_confidence]

        # Sort by priority and confidence
        alerts.sort(key=lambda x: (x.priority.value, x.confidence), reverse=True)

        # Limit to max alerts
        alerts = alerts[:self.max_alerts]

        print(f"   ✅ Generated {len(alerts)} high-priority alerts")

        return alerts

    def _extract_metric(self, item, key: str, default=None):
        """Read a metric from either a dataclass-style object or dict."""
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    def _detect_player_inactivity(self, tracks: Dict, analytics: Dict) -> List[Alert]:
        """
        Detect players who are not moving enough
        """
        alerts = []

        for player_id, stats in iter_player_stats(analytics):
            team = stats.get('team', 1)
            distance = stats.get('total_distance_m', stats.get('total_distance_covered', 0))
            frames = stats.get('frames_tracked', get_player_frame_count(tracks, player_id))

            # Convert to distance per 5 minutes
            if frames > 0:
                minutes = frames / (self.fps * 60)
                distance_per_5min = (distance / minutes) * 5 if minutes > 0 else 0

                if distance_per_5min < self.thresholds['inactivity_distance']:
                    confidence = 1.0 - (distance_per_5min / self.thresholds['inactivity_distance'])

                    alert = Alert(
                        alert_type=AlertType.PLAYER_INACTIVITY,
                        priority=AlertPriority.HIGH,
                        player_id=player_id,
                        team=team,
                        frame_range=(0, frames),
                        confidence=min(confidence, 0.95),
                        title=f"Player #{player_id} Low Activity",
                        description=f"Player #{player_id} only covered {distance:.0f}m ({distance_per_5min:.0f}m per 5min)",
                        recommendation=f"Check if player is injured or fatigued. Consider substitution.",
                        metrics={
                            'total_distance': distance,
                            'distance_per_5min': distance_per_5min,
                            'threshold': self.thresholds['inactivity_distance']
                        }
                    )
                    alerts.append(alert)

        return alerts

    def _detect_player_overload(self,
                                tracks: Dict,
                                analytics: Dict,
                                fatigue_data: Dict = None) -> List[Alert]:
        """
        Detect players working too hard (injury risk)
        """
        alerts = []

        for player_id, stats in iter_player_stats(analytics):
            team = stats.get('team', 1)
            distance = stats.get('total_distance_m', stats.get('total_distance_covered', 0))
            frames = stats.get('frames_tracked', get_player_frame_count(tracks, player_id))

            # Extrapolate to 45 minutes
            if frames > 0:
                minutes = frames / (self.fps * 60)
                distance_45min = (distance / minutes) * 45 if minutes > 0 else 0

                if distance_45min > self.thresholds['overload_distance']:
                    confidence = min((distance_45min - self.thresholds['overload_distance']) / 2000, 0.95)

                    alert = Alert(
                        alert_type=AlertType.PLAYER_OVERLOAD,
                        priority=AlertPriority.CRITICAL,
                        player_id=player_id,
                        team=team,
                        frame_range=(0, frames),
                        confidence=confidence,
                        title=f"Player #{player_id} Overload Risk",
                        description=f"Player #{player_id} on pace for {distance_45min:.0f}m in 45min (threshold: {self.thresholds['overload_distance']}m)",
                        recommendation=f"Reduce workload or substitute to prevent injury",
                        metrics={
                            'current_distance': distance,
                            'projected_45min': distance_45min,
                            'threshold': self.thresholds['overload_distance']
                        }
                    )
                    alerts.append(alert)

        return alerts

    def _detect_defensive_gaps(self, tracks: Dict, formations: Dict = None) -> List[Alert]:
        """
        Detect dangerous gaps in defensive line
        """
        alerts = []

        if not tracks or 'players' not in tracks:
            return alerts

        # Analyze each frame for defensive gaps
        player_frames = get_player_frames(tracks)
        frame_numbers = get_frame_numbers(tracks)
        gap_frames = []

        for frame_num in frame_numbers:
            frame_data = player_frames[frame_num]

            # Separate teams
            team1_positions = []
            team2_positions = []

            for player_id, data in frame_data.items():
                team = data.get('team', 1)
                bbox = data.get('bbox', [])

                if len(bbox) >= 4:
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2

                    if team == 1:
                        team1_positions.append((center_x, center_y))
                    else:
                        team2_positions.append((center_x, center_y))

            # Check Team 1 defensive gaps
            if len(team1_positions) >= 3:
                gap = self._calculate_max_gap(team1_positions)
                if gap > self.thresholds['defensive_gap']:
                    gap_frames.append((frame_num, 1, gap))

            # Check Team 2 defensive gaps
            if len(team2_positions) >= 3:
                gap = self._calculate_max_gap(team2_positions)
                if gap > self.thresholds['defensive_gap']:
                    gap_frames.append((frame_num, 2, gap))

        # Create alerts for persistent gaps (5+ seconds)
        if gap_frames:
            # Group consecutive frames
            grouped = self._group_consecutive_frames(gap_frames, window=5*self.fps)

            for frame_start, frame_end, team, avg_gap in grouped:
                confidence = min((avg_gap - self.thresholds['defensive_gap']) / 20, 0.95)

                alert = Alert(
                    alert_type=AlertType.DEFENSIVE_GAP,
                    priority=AlertPriority.CRITICAL,
                    player_id=None,
                    team=team,
                    frame_range=(frame_start, frame_end),
                    confidence=confidence,
                    title=f"Team {team} Defensive Gap",
                    description=f"Dangerous gap of {avg_gap:.1f}m in defensive line",
                    recommendation=f"Compress defensive line, check positioning",
                    metrics={
                        'max_gap': avg_gap,
                        'threshold': self.thresholds['defensive_gap'],
                        'duration_seconds': (frame_end - frame_start) / self.fps
                    }
                )
                alerts.append(alert)

        return alerts

    def _calculate_max_gap(self, positions: List[Tuple[float, float]]) -> float:
        """Calculate maximum gap between adjacent players"""
        if len(positions) < 2:
            return 0.0

        # Sort by x-coordinate
        sorted_pos = sorted(positions, key=lambda p: p[0])

        max_gap = 0.0
        for i in range(len(sorted_pos) - 1):
            gap = np.sqrt((sorted_pos[i+1][0] - sorted_pos[i][0])**2 +
                         (sorted_pos[i+1][1] - sorted_pos[i][1])**2)
            max_gap = max(max_gap, gap)

        return max_gap

    def _group_consecutive_frames(self, frames: List, window: int) -> List:
        """Group consecutive frames with similar issues"""
        if not frames:
            return []

        grouped = []
        current_group = [frames[0]]

        for i in range(1, len(frames)):
            if frames[i][0] - current_group[-1][0] <= window and frames[i][1] == current_group[0][1]:
                current_group.append(frames[i])
            else:
                if len(current_group) >= 3:  # At least 3 frames
                    frame_start = current_group[0][0]
                    frame_end = current_group[-1][0]
                    team = current_group[0][1]
                    avg_gap = np.mean([f[2] for f in current_group])
                    grouped.append((frame_start, frame_end, team, avg_gap))
                current_group = [frames[i]]

        # Add last group
        if len(current_group) >= 3:
            frame_start = current_group[0][0]
            frame_end = current_group[-1][0]
            team = current_group[0][1]
            avg_gap = np.mean([f[2] for f in current_group])
            grouped.append((frame_start, frame_end, team, avg_gap))

        return grouped

    def _detect_fatigue_warnings(self, fatigue_data: Dict = None) -> List[Alert]:
        """Detect players showing fatigue symptoms"""
        alerts = []

        if not fatigue_data:
            return alerts

        for player_id, fatigue_info in fatigue_data.items():
            fatigue_score = self._extract_metric(fatigue_info, 'fatigue_score', 0.0)
            team = self._extract_metric(fatigue_info, 'team', 1)
            frames = self._extract_metric(
                fatigue_info,
                'frames_analyzed',
                self._extract_metric(fatigue_info, 'frames', 0),
            )

            if fatigue_score > self.thresholds['fatigue_score']:
                confidence = min(fatigue_score, 0.95)

                alert = Alert(
                    alert_type=AlertType.FATIGUE_WARNING,
                    priority=AlertPriority.HIGH,
                    player_id=player_id,
                    team=team,
                    frame_range=(0, frames),
                    confidence=confidence,
                    title=f"Player #{player_id} Fatigue Warning",
                    description=f"Player #{player_id} showing high fatigue (score: {fatigue_score:.2f})",
                    recommendation=f"Consider rest or substitution",
                    metrics={
                        'fatigue_score': fatigue_score,
                        'sprints': self._extract_metric(fatigue_info, 'sprint_count', 0),
                        'high_intensity_distance': self._extract_metric(fatigue_info, 'high_intensity_distance', 0),
                    }
                )
                alerts.append(alert)

        return alerts

    def _detect_formation_breaks(self, tracks: Dict, formations: Dict = None) -> List[Alert]:
        """Detect when formation structure breaks down"""
        alerts = []

        # TODO: Implement after formation_detector.py is created
        # Will check deviation from expected formation positions

        return alerts

    def _detect_possession_issues(self, analytics: Dict) -> List[Alert]:
        """Detect sudden possession loss patterns"""
        alerts = []

        # Get possession time series
        ball_possession = analytics.get('ball_possession', {})

        if not ball_possession:
            return alerts

        # TODO: Analyze possession trends over time windows
        # Alert if sudden 30%+ drop in 5-minute window

        return alerts

    def _detect_pressing_failures(self, tracks: Dict, analytics: Dict) -> List[Alert]:
        """Detect when pressing intensity drops"""
        alerts = []

        # TODO: Implement after pressing_analyzer.py is created
        # Will check team compactness and pressing intensity

        return alerts

    def _detect_injury_risks(self, fatigue_data: Dict = None, analytics: Dict = None) -> List[Alert]:
        """Detect high injury risk situations"""
        alerts = []

        if not fatigue_data:
            return alerts

        for player_id, fatigue_info in fatigue_data.items():
            # Calculate injury risk score
            fatigue_score = self._extract_metric(fatigue_info, 'fatigue_score', 0.0)
            sprint_count = self._extract_metric(fatigue_info, 'sprint_count', 0)
            frames = self._extract_metric(
                fatigue_info,
                'frames_analyzed',
                self._extract_metric(fatigue_info, 'frames', 1),
            )
            team = self._extract_metric(fatigue_info, 'team', 1)

            # Sprint frequency (sprints per minute)
            minutes = frames / (self.fps * 60)
            sprint_frequency = sprint_count / minutes if minutes > 0 else 0

            # Combined injury risk
            injury_risk = (fatigue_score * 0.6) + min(sprint_frequency / 5, 1.0) * 0.4

            if injury_risk > self.thresholds['injury_risk_score']:
                confidence = min(injury_risk, 0.95)

                alert = Alert(
                    alert_type=AlertType.INJURY_RISK,
                    priority=AlertPriority.CRITICAL,
                    player_id=player_id,
                    team=team,
                    frame_range=(0, frames),
                    confidence=confidence,
                    title=f"Player #{player_id} Injury Risk",
                    description=f"High injury risk: {injury_risk:.2f} (fatigue + sprint frequency)",
                    recommendation=f"URGENT: Reduce intensity or substitute immediately",
                    metrics={
                        'injury_risk_score': injury_risk,
                        'fatigue_score': fatigue_score,
                        'sprint_frequency': sprint_frequency
                    }
                )
                alerts.append(alert)

        return alerts

    def _detect_positional_errors(self, tracks: Dict, formations: Dict = None) -> List[Alert]:
        """Detect players out of position"""
        alerts = []

        # TODO: Implement after formation_detector.py is created
        # Will check deviation from expected tactical positions

        return alerts

    def _detect_tactical_imbalances(self, tracks: Dict, analytics: Dict) -> List[Alert]:
        """Detect overall tactical imbalances (too attacking/defensive)"""
        alerts = []

        # TODO: Implement after tactical zone analysis is ready
        # Will check player distribution across pitch thirds

        return alerts

    def export_alerts_to_dict(self, alerts: List[Alert]) -> Dict:
        """
        Export alerts to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'total_alerts': len(alerts),
            'critical_count': sum(1 for a in alerts if a.priority == AlertPriority.CRITICAL),
            'high_count': sum(1 for a in alerts if a.priority == AlertPriority.HIGH),
            'medium_count': sum(1 for a in alerts if a.priority == AlertPriority.MEDIUM),
            'alerts': [
                {
                    'type': alert.alert_type.value,
                    'priority': alert.priority.name,
                    'player_id': alert.player_id,
                    'team': alert.team,
                    'frame_range': alert.frame_range,
                    'confidence': round(alert.confidence, 3),
                    'title': alert.title,
                    'description': alert.description,
                    'recommendation': alert.recommendation,
                    'metrics': alert.metrics
                }
                for alert in alerts
            ]
        }

    def generate_alert_summary(self, alerts: List[Alert]) -> str:
        """Generate human-readable alert summary"""
        if not alerts:
            return "✅ No critical issues detected. Team performing well."

        summary = f"🚨 {len(alerts)} Alert(s) Detected:\n\n"

        for i, alert in enumerate(alerts, 1):
            priority_icon = "🔴" if alert.priority == AlertPriority.CRITICAL else "🟠" if alert.priority == AlertPriority.HIGH else "🟡"
            player_info = f"Player #{alert.player_id}" if alert.player_id else f"Team {alert.team}"

            summary += f"{priority_icon} {i}. {alert.title}\n"
            summary += f"   {alert.description}\n"
            summary += f"   💡 {alert.recommendation}\n\n"

        return summary
