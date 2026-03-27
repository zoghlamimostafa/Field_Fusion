#!/usr/bin/env python3
"""
Confidence Scorer - Week 2, Day 12-13
Tunisia Football AI Level 3

Calculates confidence scores for all metrics and analytics.
Essential for Level 3 SaaS - tells coaches how much to trust each insight.

Features:
- Data quality assessment
- Sample size validation
- Calibration quality scoring
- Variance analysis
- Per-metric confidence
- Overall analysis confidence
- Microservice-ready architecture
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from utils.track_data_utils import count_player_stats, get_player_frames


@dataclass
class ConfidenceScore:
    """Confidence scoring for analytics"""
    overall_confidence: float  # 0-1 scale

    # Component scores
    data_quality: float  # How clean/complete is the data
    sample_size: float  # Enough data for reliable insights
    calibration_quality: float  # How good is pitch calibration
    consistency: float  # How consistent are measurements

    # Per-metric confidence
    tracking_confidence: float
    team_assignment_confidence: float
    ball_possession_confidence: float
    speed_distance_confidence: float
    event_detection_confidence: float
    formation_confidence: float
    fatigue_confidence: float
    pressing_confidence: float

    # Reliability indicators
    frames_analyzed: int
    players_tracked: int
    missing_data_percent: float

    # Recommendations
    reliability_level: str  # "High", "Medium", "Low"
    warnings: List[str]


class ConfidenceScorer:
    """
    Calculates confidence scores for all analytics
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self, fps: int = 25):
        self.fps = fps

        # Minimum thresholds for reliable analysis
        self.min_frames = 250  # ~10 seconds
        self.min_players_per_team = 8
        self.min_ball_detection_rate = 0.5  # 50% of frames
        self.min_tracking_persistence = 0.7  # Players tracked 70% of time

    def calculate_confidence(self,
                            tracks: Dict,
                            analytics: Dict,
                            pitch_calibration: Dict,
                            formations: Dict = None,
                            fatigue_data: Dict = None,
                            pressing_data: Dict = None) -> ConfidenceScore:
        """
        Calculate overall confidence score for analysis

        Args:
            tracks: Player tracking data
            analytics: Match analytics
            pitch_calibration: Pitch calibration metadata
            formations: Formation detection results
            fatigue_data: Fatigue analysis results
            pressing_data: Pressing analysis results

        Returns:
            ConfidenceScore object
        """
        print("\n📊 Calculating Confidence Scores...")

        warnings = []

        # 1. Data quality assessment
        data_quality, data_warnings = self._assess_data_quality(tracks, analytics)
        warnings.extend(data_warnings)

        # 2. Sample size validation
        sample_size, sample_warnings = self._validate_sample_size(tracks, analytics)
        warnings.extend(sample_warnings)

        # 3. Calibration quality
        calibration_quality, calib_warnings = self._assess_calibration_quality(pitch_calibration)
        warnings.extend(calib_warnings)

        # 4. Consistency check
        consistency, consistency_warnings = self._check_consistency(tracks, analytics)
        warnings.extend(consistency_warnings)

        # 5. Per-metric confidence
        tracking_conf = self._score_tracking_confidence(tracks, data_quality, sample_size)
        team_conf = self._score_team_assignment_confidence(tracks, analytics, consistency)
        possession_conf = self._score_possession_confidence(analytics, data_quality)
        speed_conf = self._score_speed_distance_confidence(analytics, calibration_quality, sample_size)
        event_conf = self._score_event_detection_confidence(analytics, sample_size)
        formation_conf = self._score_formation_confidence(formations, sample_size) if formations else 0.0
        fatigue_conf = self._score_fatigue_confidence(fatigue_data, sample_size) if fatigue_data else 0.0
        pressing_conf = self._score_pressing_confidence(pressing_data, sample_size) if pressing_data else 0.0

        # 6. Overall confidence (weighted average)
        overall_confidence = self._calculate_overall_confidence(
            data_quality, sample_size, calibration_quality, consistency,
            tracking_conf, team_conf, possession_conf, speed_conf, event_conf
        )

        # 7. Reliability level
        reliability_level = self._determine_reliability_level(overall_confidence)

        # 8. Calculate metadata
        player_frames = get_player_frames(tracks)
        frames_analyzed = len(player_frames)
        players_tracked = count_player_stats(analytics)
        missing_data_pct = self._calculate_missing_data_percent(tracks)

        score = ConfidenceScore(
            overall_confidence=overall_confidence,
            data_quality=data_quality,
            sample_size=sample_size,
            calibration_quality=calibration_quality,
            consistency=consistency,
            tracking_confidence=tracking_conf,
            team_assignment_confidence=team_conf,
            ball_possession_confidence=possession_conf,
            speed_distance_confidence=speed_conf,
            event_detection_confidence=event_conf,
            formation_confidence=formation_conf,
            fatigue_confidence=fatigue_conf,
            pressing_confidence=pressing_conf,
            frames_analyzed=frames_analyzed,
            players_tracked=players_tracked,
            missing_data_percent=missing_data_pct,
            reliability_level=reliability_level,
            warnings=warnings
        )

        print(f"   Overall Confidence: {overall_confidence:.2f} ({reliability_level})")
        if warnings:
            print(f"   ⚠️  {len(warnings)} warning(s)")

        return score

    def _assess_data_quality(self, tracks: Dict, analytics: Dict) -> Tuple[float, List[str]]:
        """Assess overall data quality"""
        warnings = []
        scores = []

        # Check tracking completeness
        player_frames = get_player_frames(tracks)
        if not player_frames:
            warnings.append("No player tracking data available")
            scores.append(0.0)
        else:
            # Check for gaps in tracking
            frame_nums = sorted(player_frames.keys())
            if len(frame_nums) > 1:
                expected_frames = frame_nums[-1] - frame_nums[0] + 1
                actual_frames = len(frame_nums)
                completeness = actual_frames / expected_frames
                scores.append(completeness)

                if completeness < 0.9:
                    warnings.append(f"Tracking has gaps: {completeness*100:.1f}% completeness")

        # Check ball detection
        if 'ball' not in tracks or not tracks['ball']:
            warnings.append("No ball tracking data")
            scores.append(0.0)
        else:
            ball_detection_rate = len(tracks['ball']) / max(len(player_frames), 1)
            scores.append(ball_detection_rate)

            if ball_detection_rate < self.min_ball_detection_rate:
                warnings.append(f"Low ball detection: {ball_detection_rate*100:.1f}%")

        # Check analytics completeness
        if not analytics.get('player_stats'):
            warnings.append("No player statistics generated")
            scores.append(0.0)
        else:
            scores.append(1.0)

        quality = np.mean(scores) if scores else 0.0
        return quality, warnings

    def _validate_sample_size(self, tracks: Dict, analytics: Dict) -> Tuple[float, List[str]]:
        """Validate sample size is sufficient"""
        warnings = []

        frames = len(get_player_frames(tracks))
        players = count_player_stats(analytics)

        # Frame count score
        if frames < self.min_frames:
            warnings.append(f"Short video: only {frames} frames ({frames/self.fps:.1f}s)")
            frame_score = frames / self.min_frames
        else:
            frame_score = 1.0

        # Player count score
        if players < self.min_players_per_team * 2:
            warnings.append(f"Few players tracked: only {players} players")
            player_score = players / (self.min_players_per_team * 2)
        else:
            player_score = 1.0

        sample_score = (frame_score + player_score) / 2
        return sample_score, warnings

    def _assess_calibration_quality(self, pitch_calibration: Dict) -> Tuple[float, List[str]]:
        """Assess pitch calibration quality"""
        warnings = []

        if not pitch_calibration:
            warnings.append("No pitch calibration data")
            return 0.3, warnings  # Fallback homography = low confidence

        method = pitch_calibration.get('method', 'unknown')
        confidence = pitch_calibration.get('confidence', 0.0)

        if method == 'fallback':
            warnings.append("Using fallback pitch calibration (low accuracy)")
            return 0.3, warnings

        if method == 'keypoint_detection':
            keypoints_matched = pitch_calibration.get('keypoints_matched', 0)

            if keypoints_matched < 4:
                warnings.append(f"Few keypoints matched: {keypoints_matched}")
                return 0.5, warnings

            if confidence < 0.6:
                warnings.append(f"Low calibration confidence: {confidence:.2f}")

            return confidence, warnings

        return 0.5, warnings

    def _check_consistency(self, tracks: Dict, analytics: Dict) -> Tuple[float, List[str]]:
        """Check consistency of measurements"""
        warnings = []
        scores = []

        # Check player ID consistency (should not have too many IDs)
        player_count = count_player_stats(analytics)
        if player_count > 30:  # More than 15 per team is suspicious
            warnings.append(f"Too many player IDs: {player_count} (ID fragmentation?)")
            scores.append(0.5)
        else:
            scores.append(1.0)

        # Check possession totals (should add to 100%)
        team_stats = analytics.get('team_stats', {})
        if team_stats:
            team1_poss = team_stats.get('team_1', {}).get('possession_percent', 0)
            team2_poss = team_stats.get('team_2', {}).get('possession_percent', 0)
            total_poss = team1_poss + team2_poss

            if abs(total_poss - 100) > 5:
                warnings.append(f"Possession totals inconsistent: {total_poss:.1f}%")
                scores.append(0.7)
            else:
                scores.append(1.0)

        consistency = np.mean(scores) if scores else 0.8
        return consistency, warnings

    def _score_tracking_confidence(self, tracks: Dict, data_quality: float, sample_size: float) -> float:
        """Score tracking confidence"""
        return (data_quality * 0.6 + sample_size * 0.4)

    def _score_team_assignment_confidence(self, tracks: Dict, analytics: Dict, consistency: float) -> float:
        """Score team assignment confidence"""
        # Based on consistency (fewer ID issues = better team assignment)
        return consistency * 0.9  # Slightly discount

    def _score_possession_confidence(self, analytics: Dict, data_quality: float) -> float:
        """Score ball possession confidence"""
        # Depends on ball detection quality
        return data_quality * 0.85

    def _score_speed_distance_confidence(self, analytics: Dict, calibration: float, sample_size: float) -> float:
        """Score speed/distance confidence"""
        # Heavily depends on calibration quality
        return (calibration * 0.7 + sample_size * 0.3)

    def _score_event_detection_confidence(self, analytics: Dict, sample_size: float) -> float:
        """Score event detection confidence"""
        # Rule-based events have moderate confidence
        return sample_size * 0.7  # Max 0.7 for rule-based detection

    def _score_formation_confidence(self, formations: Dict, sample_size: float) -> float:
        """Score formation detection confidence"""
        if not formations:
            return 0.0

        # Use formation's own confidence
        confidences = [f.confidence for f in formations.values()]
        return np.mean(confidences) * sample_size

    def _score_fatigue_confidence(self, fatigue_data: Dict, sample_size: float) -> float:
        """Score fatigue estimation confidence"""
        if not fatigue_data:
            return 0.0

        # Fatigue needs longer videos for accuracy
        return sample_size * 0.8

    def _score_pressing_confidence(self, pressing_data: Dict, sample_size: float) -> float:
        """Score pressing analysis confidence"""
        if not pressing_data:
            return 0.0

        return sample_size * 0.75

    def _calculate_overall_confidence(self,
                                     data_quality: float,
                                     sample_size: float,
                                     calibration: float,
                                     consistency: float,
                                     tracking: float,
                                     team: float,
                                     possession: float,
                                     speed: float,
                                     events: float) -> float:
        """Calculate weighted overall confidence"""
        weights = {
            'data_quality': 0.15,
            'sample_size': 0.10,
            'calibration': 0.15,
            'consistency': 0.10,
            'tracking': 0.15,
            'team': 0.10,
            'possession': 0.10,
            'speed': 0.10,
            'events': 0.05
        }

        overall = (
            weights['data_quality'] * data_quality +
            weights['sample_size'] * sample_size +
            weights['calibration'] * calibration +
            weights['consistency'] * consistency +
            weights['tracking'] * tracking +
            weights['team'] * team +
            weights['possession'] * possession +
            weights['speed'] * speed +
            weights['events'] * events
        )

        return min(overall, 1.0)

    def _determine_reliability_level(self, confidence: float) -> str:
        """Determine reliability level from confidence score"""
        if confidence >= 0.75:
            return "High"
        elif confidence >= 0.50:
            return "Medium"
        else:
            return "Low"

    def _calculate_missing_data_percent(self, tracks: Dict) -> float:
        """Calculate percentage of missing/incomplete data"""
        player_frames = get_player_frames(tracks)
        if not player_frames:
            return 100.0

        total_expected = 0
        total_missing = 0

        for frame_data in player_frames.values():
            total_expected += 22  # Expect 22 players
            total_missing += max(0, 22 - len(frame_data))

        if total_expected == 0:
            return 100.0

        return (total_missing / total_expected) * 100

    def export_confidence_data(self, score: ConfidenceScore) -> Dict:
        """
        Export confidence data to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'overall': {
                'confidence': round(score.overall_confidence, 3),
                'reliability_level': score.reliability_level
            },
            'components': {
                'data_quality': round(score.data_quality, 3),
                'sample_size': round(score.sample_size, 3),
                'calibration_quality': round(score.calibration_quality, 3),
                'consistency': round(score.consistency, 3)
            },
            'per_metric': {
                'tracking': round(score.tracking_confidence, 3),
                'team_assignment': round(score.team_assignment_confidence, 3),
                'ball_possession': round(score.ball_possession_confidence, 3),
                'speed_distance': round(score.speed_distance_confidence, 3),
                'event_detection': round(score.event_detection_confidence, 3),
                'formation': round(score.formation_confidence, 3),
                'fatigue': round(score.fatigue_confidence, 3),
                'pressing': round(score.pressing_confidence, 3)
            },
            'metadata': {
                'frames_analyzed': score.frames_analyzed,
                'players_tracked': score.players_tracked,
                'missing_data_percent': round(score.missing_data_percent, 1)
            },
            'warnings': score.warnings
        }

    def generate_confidence_summary(self, score: ConfidenceScore) -> str:
        """Generate human-readable confidence summary"""
        summary = f"📊 Analysis Confidence: {score.overall_confidence:.2f} ({score.reliability_level})\n\n"

        summary += "Component Scores:\n"
        summary += f"   Data Quality: {score.data_quality:.2f}\n"
        summary += f"   Sample Size: {score.sample_size:.2f}\n"
        summary += f"   Calibration: {score.calibration_quality:.2f}\n"
        summary += f"   Consistency: {score.consistency:.2f}\n\n"

        if score.warnings:
            summary += f"⚠️  Warnings ({len(score.warnings)}):\n"
            for warning in score.warnings[:5]:  # Show max 5 warnings
                summary += f"   - {warning}\n"

        return summary
