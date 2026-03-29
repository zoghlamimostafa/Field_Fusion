"""
Opposition Scouting System
==========================

Comprehensive opponent analysis and tactical intelligence for:
- Team playing style identification
- Key player identification and profiling
- Tactical weaknesses detection
- Formation patterns and transitions
- Set-piece tendencies
- Pressing vulnerabilities
- Counter-attack susceptibility

Generates actionable tactical recommendations for coaches.

Based on professional scouting methodologies used by elite clubs.
"""

import numpy as np
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


class PlayingStyle(Enum):
    """Team playing style categories"""
    POSSESSION_BASED = "possession_based"
    COUNTER_ATTACK = "counter_attack"
    DIRECT_PLAY = "direct_play"
    HIGH_PRESSING = "high_pressing"
    LOW_BLOCK = "low_block"
    BALANCED = "balanced"


class DefensiveStyle(Enum):
    """Defensive organization styles"""
    HIGH_LINE = "high_line"
    MID_BLOCK = "mid_block"
    LOW_BLOCK = "low_block"
    AGGRESSIVE_PRESS = "aggressive_press"
    ZONAL = "zonal"
    MAN_MARKING = "man_marking"


@dataclass
class KeyPlayer:
    """Key player profile for opponent team"""
    player_id: int
    name: str
    position: str

    # Influence metrics
    touches_per_90: float
    pass_completion: float
    key_passes_per_90: float
    goals_per_90: float
    assists_per_90: float

    # Tactical role
    role_description: str  # "Playmaker", "Target Man", etc.

    # Weaknesses to exploit
    weaknesses: List[str]

    # Threat level (0-10)
    threat_level: float


@dataclass
class TacticalWeakness:
    """Identified tactical weakness"""
    weakness_type: str
    severity: float  # 0-10 scale
    description: str
    how_to_exploit: str
    evidence: List[str]  # Specific examples
    confidence: float


@dataclass
class SetPieceTendency:
    """Set piece patterns and tendencies"""
    set_piece_type: str  # "corner", "free_kick", "throw_in"
    common_routines: List[Dict]
    target_players: List[int]
    success_rate: float
    defensive_vulnerabilities: List[str]


@dataclass
class OppositionReport:
    """Complete opposition scouting report"""
    team_id: int
    team_name: str
    matches_analyzed: int
    analysis_date: str

    # Playing style
    primary_playing_style: str
    style_confidence: float
    possession_avg: float
    passing_accuracy: float
    avg_passes_per_possession: float

    # Formation
    primary_formation: str
    formation_variants: List[str]
    formation_change_triggers: List[str]

    # Defensive organization
    defensive_style: str
    defensive_line_avg: float  # Average defensive line height (meters)
    pressing_intensity: float  # 0-1 scale
    ppda: float  # Passes Per Defensive Action

    # Offensive patterns
    attack_style: str
    direct_play_percentage: float
    counter_attack_frequency: float
    crossing_frequency: float
    through_ball_frequency: float

    # Key players
    key_players: List[KeyPlayer]
    most_influential_player: Dict

    # Tactical weaknesses
    exploitable_weaknesses: List[TacticalWeakness]

    # Set pieces
    set_piece_analysis: List[SetPieceTendency]

    # Recommendations
    tactical_recommendations: List[str]
    lineup_suggestions: List[str]
    specific_instructions: List[str]

    # Confidence
    overall_confidence: float


class OppositionScoutingSystem:
    """
    Comprehensive opposition scouting and tactical analysis
    """

    def __init__(self):
        # Playing style thresholds
        self.style_thresholds = {
            'possession_based': {'possession': 55, 'passes_per_possession': 6},
            'counter_attack': {'possession': 45, 'direct_play_pct': 40},
            'high_pressing': {'ppda': 10, 'defensive_line': 50},
            'low_block': {'ppda': 15, 'defensive_line': 35},
        }

    def identify_playing_style(
        self,
        possession_pct: float,
        passes_per_possession: float,
        direct_play_pct: float,
        ppda: float,
        defensive_line_height: float
    ) -> Tuple[PlayingStyle, float]:
        """
        Identify team's primary playing style
        Returns: (style, confidence)
        """
        style_scores = {}

        # Possession-based
        if possession_pct > 55 and passes_per_possession > 6:
            style_scores[PlayingStyle.POSSESSION_BASED] = min(
                1.0, (possession_pct / 60) * (passes_per_possession / 8)
            )

        # Counter-attack
        if possession_pct < 50 and direct_play_pct > 35:
            style_scores[PlayingStyle.COUNTER_ATTACK] = min(
                1.0, (1 - possession_pct / 50) * (direct_play_pct / 40)
            )

        # High pressing
        if ppda < 12 and defensive_line_height > 48:
            style_scores[PlayingStyle.HIGH_PRESSING] = min(
                1.0, (1 - ppda / 12) * (defensive_line_height / 55)
            )

        # Low block
        if ppda > 14 and defensive_line_height < 38:
            style_scores[PlayingStyle.LOW_BLOCK] = min(
                1.0, (ppda / 18) * (1 - defensive_line_height / 40)
            )

        # Direct play
        if direct_play_pct > 45:
            style_scores[PlayingStyle.DIRECT_PLAY] = direct_play_pct / 60

        # Balanced (fallback)
        if not style_scores or max(style_scores.values()) < 0.6:
            return PlayingStyle.BALANCED, 0.7

        # Return highest scoring style
        primary_style = max(style_scores, key=style_scores.get)
        confidence = style_scores[primary_style]

        return primary_style, confidence

    def identify_key_players(
        self,
        analytics: Dict,
        team_id: int = 2,
        top_n: int = 5
    ) -> List[KeyPlayer]:
        """
        Identify opponent's key players and their roles
        """
        key_players = []

        player_stats = analytics.get('player_stats', {})
        team_possession = analytics.get('team_possession', {}).get(team_id, 50.0)

        # Calculate influence scores for each player
        player_influences = []

        for player_id, stats in player_stats.items():
            # Filter by team
            if player_id not in range(12, 23):  # Assuming team 2 is players 12-22
                continue

            minutes = stats.get('minutes_played', 90.0)
            if minutes < 30:  # Ignore players with little playing time
                continue

            per_90 = 90.0 / minutes

            # Calculate influence score
            touches = stats.get('ball_control', 0) * per_90
            passes = stats.get('passes', 0) * per_90
            pass_completion = stats.get('pass_accuracy', 0.0)
            goals = stats.get('goals', 0) * per_90
            assists = stats.get('assists', 0) * per_90
            key_passes = assists * 3  # Estimate

            influence_score = (
                touches * 0.2 +
                passes * 0.2 +
                pass_completion * 10 +
                goals * 15 +
                assists * 12 +
                key_passes * 0.3
            )

            player_influences.append({
                'player_id': player_id,
                'influence_score': influence_score,
                'touches_per_90': touches,
                'passes_per_90': passes,
                'pass_completion': pass_completion,
                'goals_per_90': goals,
                'assists_per_90': assists,
                'key_passes_per_90': key_passes,
            })

        # Sort by influence and take top N
        player_influences.sort(key=lambda x: x['influence_score'], reverse=True)

        for i, player_data in enumerate(player_influences[:top_n]):
            # Determine role
            role = self._determine_player_role(player_data)

            # Identify weaknesses
            weaknesses = self._identify_player_weaknesses(player_data)

            # Calculate threat level
            threat_level = min(10.0, player_data['influence_score'] / 10)

            key_player = KeyPlayer(
                player_id=player_data['player_id'],
                name=f"Player_{player_data['player_id']}",
                position="Unknown",  # Would need formation data
                touches_per_90=round(player_data['touches_per_90'], 1),
                pass_completion=round(player_data['pass_completion'], 3),
                key_passes_per_90=round(player_data['key_passes_per_90'], 1),
                goals_per_90=round(player_data['goals_per_90'], 2),
                assists_per_90=round(player_data['assists_per_90'], 2),
                role_description=role,
                weaknesses=weaknesses,
                threat_level=round(threat_level, 1)
            )

            key_players.append(key_player)

        return key_players

    def _determine_player_role(self, player_data: Dict) -> str:
        """Determine player's tactical role"""
        goals = player_data['goals_per_90']
        assists = player_data['assists_per_90']
        passes = player_data['passes_per_90']

        if goals > 0.5:
            return "Goal Threat"
        elif assists > 0.3:
            return "Playmaker"
        elif passes > 50:
            return "Deep-Lying Playmaker"
        elif passes > 30:
            return "Box-to-Box Midfielder"
        else:
            return "Ball Carrier"

    def _identify_player_weaknesses(self, player_data: Dict) -> List[str]:
        """Identify exploitable weaknesses in player"""
        weaknesses = []

        if player_data['pass_completion'] < 0.75:
            weaknesses.append("Poor passing accuracy - press aggressively")

        if player_data['touches_per_90'] > 80:
            weaknesses.append("High ball involvement - isolate to disrupt team")

        if player_data['goals_per_90'] > 0.4:
            weaknesses.append("Primary goal threat - tight marking required")

        return weaknesses

    def detect_tactical_weaknesses(
        self,
        analytics: Dict,
        formations: Optional[Dict] = None,
        pressing_data: Optional[Dict] = None,
        pass_networks: Optional[Dict] = None,
        team_id: int = 2
    ) -> List[TacticalWeakness]:
        """
        Detect exploitable tactical weaknesses
        """
        weaknesses = []

        # 1. Defensive line vulnerability
        if formations and team_id in formations:
            formation_data = formations[team_id]
            defensive_line_height = formation_data.get('shape_metrics', {}).get('depth', 50)

            if defensive_line_height > 55:
                weaknesses.append(TacticalWeakness(
                    weakness_type="High Defensive Line",
                    severity=8.0,
                    description="Team plays with high defensive line (>55m from own goal)",
                    how_to_exploit="Use through balls and pace in attack. Target space behind defense.",
                    evidence=["Average defensive line: {:.1f}m".format(defensive_line_height)],
                    confidence=0.85
                ))

        # 2. Poor pressing coordination
        if pressing_data and team_id in pressing_data:
            team_pressing = pressing_data[team_id]
            ppda = team_pressing.get('ppda', 15)
            pressing_intensity = team_pressing.get('pressing_intensity', 0.5)

            if ppda > 15 and pressing_intensity < 0.4:
                weaknesses.append(TacticalWeakness(
                    weakness_type="Passive Pressing",
                    severity=7.0,
                    description="Team rarely presses high, allowing easy build-up play",
                    how_to_exploit="Build from back patiently. Dominate possession in midfield.",
                    evidence=[f"PPDA: {ppda:.1f}", f"Pressing intensity: {pressing_intensity:.2f}"],
                    confidence=0.80
                ))

        # 3. Weak passing connections
        if pass_networks and team_id in pass_networks:
            network_data = pass_networks[team_id]
            isolated_players = network_data.get('isolated_players', [])

            if isolated_players:
                weaknesses.append(TacticalWeakness(
                    weakness_type="Isolated Players",
                    severity=6.5,
                    description=f"{len(isolated_players)} players poorly integrated in passing network",
                    how_to_exploit="Force play through isolated players. Press passing lanes to key players.",
                    evidence=[f"Isolated players: {isolated_players}"],
                    confidence=0.75
                ))

        # 4. Width vulnerability
        team_stats = analytics.get('team_stats', {}).get(team_id, {})
        if formations and team_id in formations:
            width = formations[team_id].get('shape_metrics', {}).get('width', 50)

            if width < 35:
                weaknesses.append(TacticalWeakness(
                    weakness_type="Narrow Shape",
                    severity=7.5,
                    description="Team plays narrow, leaving wings exposed",
                    how_to_exploit="Attack down flanks. Use wingers and overlapping fullbacks.",
                    evidence=[f"Average width: {width:.1f}m"],
                    confidence=0.82
                ))

        # 5. Transition vulnerability
        possession_pct = analytics.get('team_possession', {}).get(team_id, 50.0)
        if possession_pct > 60:
            weaknesses.append(TacticalWeakness(
                weakness_type="Transition Defense",
                severity=6.0,
                description="High possession team vulnerable to counter-attacks",
                how_to_exploit="Sit deep, win ball, counter quickly. Direct passes to forwards.",
                evidence=[f"Possession: {possession_pct:.1f}%"],
                confidence=0.70
            ))

        # Sort by severity
        weaknesses.sort(key=lambda x: x.severity, reverse=True)

        return weaknesses

    def analyze_set_pieces(
        self,
        analytics: Dict,
        team_id: int = 2
    ) -> List[SetPieceTendency]:
        """
        Analyze set piece tendencies
        """
        set_pieces = []

        # Get events
        events = analytics.get('events', {})

        # Corner analysis (placeholder - would need event data)
        corner_tendency = SetPieceTendency(
            set_piece_type="corner",
            common_routines=[
                {"routine": "Short corner", "frequency": 0.3},
                {"routine": "Near post", "frequency": 0.4},
                {"routine": "Far post", "frequency": 0.3}
            ],
            target_players=[14, 18],  # Placeholder
            success_rate=0.12,
            defensive_vulnerabilities=["Weak zonal marking", "Poor near post coverage"]
        )
        set_pieces.append(corner_tendency)

        # Free kick analysis
        freekick_tendency = SetPieceTendency(
            set_piece_type="free_kick",
            common_routines=[
                {"routine": "Direct shot", "frequency": 0.6},
                {"routine": "Layoff", "frequency": 0.2},
                {"routine": "Cross", "frequency": 0.2}
            ],
            target_players=[10],  # Placeholder
            success_rate=0.08,
            defensive_vulnerabilities=["Poor wall positioning"]
        )
        set_pieces.append(freekick_tendency)

        return set_pieces

    def generate_tactical_recommendations(
        self,
        weaknesses: List[TacticalWeakness],
        key_players: List[KeyPlayer],
        playing_style: str
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Generate tactical recommendations for coaches
        Returns: (tactical_recs, lineup_suggestions, specific_instructions)
        """
        tactical_recs = []
        lineup_suggestions = []
        specific_instructions = []

        # Based on playing style
        if playing_style == PlayingStyle.POSSESSION_BASED.value:
            tactical_recs.append("Press high to disrupt their build-up play")
            tactical_recs.append("Compact shape to reduce passing options")
            lineup_suggestions.append("Select energetic midfielders for pressing")

        elif playing_style == PlayingStyle.COUNTER_ATTACK.value:
            tactical_recs.append("Control possession to prevent counter-attacks")
            tactical_recs.append("High defensive line to compress space")
            lineup_suggestions.append("Fast defenders to track counter-attacks")

        elif playing_style == PlayingStyle.LOW_BLOCK.value:
            tactical_recs.append("Patience in possession to break down defense")
            tactical_recs.append("Use width to stretch their compact shape")
            lineup_suggestions.append("Creative playmakers to unlock defense")

        # Based on weaknesses
        for weakness in weaknesses[:3]:  # Top 3 weaknesses
            tactical_recs.append(f"EXPLOIT: {weakness.how_to_exploit}")

        # Based on key players
        if key_players:
            most_dangerous = key_players[0]
            specific_instructions.append(
                f"Tight marking on {most_dangerous.name} (#{most_dangerous.player_id}) - {most_dangerous.role_description}"
            )

            if len(key_players) > 1:
                specific_instructions.append(
                    f"Double up on {key_players[1].name} when they receive ball"
                )

        # General instructions
        specific_instructions.append("Communicate defensive assignments clearly")
        specific_instructions.append("Stay compact when out of possession")

        return tactical_recs, lineup_suggestions, specific_instructions

    def generate_opposition_report(
        self,
        analytics: Dict,
        formations: Optional[Dict] = None,
        pressing_data: Optional[Dict] = None,
        pass_networks: Optional[Dict] = None,
        fatigue_data: Optional[Dict] = None,
        team_id: int = 2,
        team_name: str = "Opposition"
    ) -> OppositionReport:
        """
        Generate comprehensive opposition scouting report
        """
        # Get team statistics
        team_stats = analytics.get('team_stats', {}).get(team_id, {})
        possession = analytics.get('team_possession', {}).get(team_id, 50.0)

        # Calculate metrics for style identification
        total_passes = team_stats.get('passes', 100)
        pass_accuracy = team_stats.get('pass_accuracy', 0.75)
        possessions = max(1, total_passes // 8)  # Estimate
        passes_per_possession = total_passes / possessions

        # Get pressing data
        if pressing_data and team_id in pressing_data:
            ppda = pressing_data[team_id].get('ppda', 12.0)
            pressing_intensity = pressing_data[team_id].get('pressing_intensity', 0.5)
            defensive_line = pressing_data[team_id].get('defensive_line_height', 45.0)
        else:
            ppda = 12.0
            pressing_intensity = 0.5
            defensive_line = 45.0

        # Estimate direct play percentage
        direct_play_pct = 30.0  # Placeholder

        # Identify playing style
        playing_style, style_confidence = self.identify_playing_style(
            possession, passes_per_possession, direct_play_pct,
            ppda, defensive_line
        )

        # Get formation
        if formations and team_id in formations:
            primary_formation = formations[team_id].get('formation_name', '4-4-2')
            formation_variants = []
        else:
            primary_formation = '4-4-2'
            formation_variants = []

        # Identify key players
        key_players = self.identify_key_players(analytics, team_id, top_n=5)

        # Detect weaknesses
        weaknesses = self.detect_tactical_weaknesses(
            analytics, formations, pressing_data, pass_networks, team_id
        )

        # Analyze set pieces
        set_pieces = self.analyze_set_pieces(analytics, team_id)

        # Generate recommendations
        tactical_recs, lineup_sugg, specific_instr = self.generate_tactical_recommendations(
            weaknesses, key_players, playing_style.value
        )

        # Calculate overall confidence
        confidence_factors = [
            style_confidence,
            0.8 if key_players else 0.5,
            0.8 if weaknesses else 0.6,
        ]
        overall_confidence = np.mean(confidence_factors)

        return OppositionReport(
            team_id=team_id,
            team_name=team_name,
            matches_analyzed=1,
            analysis_date=np.datetime64('today').astype(str),
            primary_playing_style=playing_style.value,
            style_confidence=round(style_confidence, 2),
            possession_avg=round(possession, 1),
            passing_accuracy=round(pass_accuracy, 3),
            avg_passes_per_possession=round(passes_per_possession, 1),
            primary_formation=primary_formation,
            formation_variants=formation_variants,
            formation_change_triggers=[],
            defensive_style="mid_block",  # Placeholder
            defensive_line_avg=round(defensive_line, 1),
            pressing_intensity=round(pressing_intensity, 2),
            ppda=round(ppda, 1),
            attack_style=playing_style.value,
            direct_play_percentage=round(direct_play_pct, 1),
            counter_attack_frequency=0.25,  # Placeholder
            crossing_frequency=0.15,
            through_ball_frequency=0.08,
            key_players=[asdict(kp) for kp in key_players],
            most_influential_player=asdict(key_players[0]) if key_players else {},
            exploitable_weaknesses=[asdict(w) for w in weaknesses],
            set_piece_analysis=[asdict(sp) for sp in set_pieces],
            tactical_recommendations=tactical_recs,
            lineup_suggestions=lineup_sugg,
            specific_instructions=specific_instr,
            overall_confidence=round(overall_confidence, 2)
        )

    def export_report(self, report: OppositionReport, output_path: str):
        """Export scouting report to JSON"""
        report_dict = asdict(report)

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"✅ Opposition scouting report saved to {output_path}")

    def print_report_summary(self, report: OppositionReport):
        """Print human-readable scouting report"""
        print("\n" + "="*60)
        print("🔍 OPPOSITION SCOUTING REPORT")
        print("="*60)

        print(f"\n👥 Team: {report.team_name}")
        print(f"   Matches Analyzed: {report.matches_analyzed}")
        print(f"   Report Date: {report.analysis_date}")
        print(f"   Confidence: {report.overall_confidence:.0%}")

        print(f"\n⚽ Playing Style: {report.primary_playing_style.upper()}")
        print(f"   Confidence: {report.style_confidence:.0%}")
        print(f"   Possession: {report.possession_avg:.1f}%")
        print(f"   Passing Accuracy: {report.passing_accuracy:.1%}")
        print(f"   Formation: {report.primary_formation}")

        print(f"\n🛡️  Defensive Organization:")
        print(f"   Style: {report.defensive_style}")
        print(f"   Defensive Line: {report.defensive_line_avg:.1f}m")
        print(f"   Pressing Intensity: {report.pressing_intensity:.2f}/1.0")
        print(f"   PPDA: {report.ppda:.1f}")

        if report.key_players:
            print(f"\n⭐ KEY PLAYERS TO WATCH:")
            for i, player in enumerate(report.key_players[:3], 1):
                print(f"   {i}. Player #{player['player_id']} ({player['role_description']})")
                print(f"      Threat Level: {player['threat_level']}/10")
                if player['weaknesses']:
                    print(f"      Weakness: {player['weaknesses'][0]}")

        if report.exploitable_weaknesses:
            print(f"\n🎯 EXPLOITABLE WEAKNESSES:")
            for i, weakness in enumerate(report.exploitable_weaknesses[:3], 1):
                print(f"   {i}. {weakness['weakness_type']} (Severity: {weakness['severity']}/10)")
                print(f"      → {weakness['how_to_exploit']}")

        print(f"\n📋 TACTICAL RECOMMENDATIONS:")
        for i, rec in enumerate(report.tactical_recommendations[:5], 1):
            print(f"   {i}. {rec}")

        print(f"\n👤 SPECIFIC INSTRUCTIONS:")
        for i, instr in enumerate(report.specific_instructions[:3], 1):
            print(f"   {i}. {instr}")

        print("\n" + "="*60)


def main():
    """Demo opposition scouting"""
    print("🔍 Opposition Scouting System Demo\n")

    # Create scouting system
    scout = OppositionScoutingSystem()

    # Demo analytics (minimal)
    demo_analytics = {
        'team_possession': {2: 58.5},
        'team_stats': {
            2: {
                'passes': 450,
                'pass_accuracy': 0.82,
                'possession': 58.5
            }
        },
        'player_stats': {
            15: {
                'minutes_played': 90,
                'ball_control': 95,
                'passes': 65,
                'pass_accuracy': 0.88,
                'goals': 1,
                'assists': 1
            },
            18: {
                'minutes_played': 90,
                'ball_control': 72,
                'passes': 48,
                'pass_accuracy': 0.85,
                'goals': 0,
                'assists': 2
            }
        }
    }

    # Generate report
    report = scout.generate_opposition_report(
        demo_analytics,
        team_id=2,
        team_name="Tunisia Opponents FC"
    )

    # Print summary
    scout.print_report_summary(report)


if __name__ == "__main__":
    main()
