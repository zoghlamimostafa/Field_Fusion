"""
Expected Goals (xG) Model for Football Analysis
===============================================

Calculates the probability of a shot resulting in a goal based on:
- Shot distance from goal
- Shot angle
- Body part used (foot, head, other)
- Shot type (open play, free kick, penalty, counter-attack)
- Defensive pressure
- Assist type
- Game state (winning, losing, drawing)

Uses ensemble approach:
1. Logistic Regression (baseline)
2. Random Forest (complex interactions)
3. XGBoost (gradient boosting)

Expected accuracy: 75-80% AUC-ROC
"""

import numpy as np
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Optional ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️  scikit-learn not available. xG model will use rule-based fallback.")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


class ShotType(Enum):
    """Type of shot attempt"""
    OPEN_PLAY = "open_play"
    FREE_KICK = "free_kick"
    PENALTY = "penalty"
    CORNER = "corner"
    COUNTER_ATTACK = "counter_attack"
    SET_PIECE = "set_piece"


class BodyPart(Enum):
    """Body part used for shot"""
    FOOT = "foot"
    HEAD = "head"
    OTHER = "other"


class AssistType(Enum):
    """Type of assist leading to shot"""
    PASS = "pass"
    CROSS = "cross"
    THROUGH_BALL = "through_ball"
    DRIBBLE = "dribble"
    REBOUND = "rebound"
    NONE = "none"


@dataclass
class ShotEvent:
    """Represents a single shot event with features"""
    distance: float  # Distance from goal center (meters)
    angle: float  # Angle to goal (degrees, 0-180)
    body_part: BodyPart
    shot_type: ShotType
    assist_type: AssistType
    defensive_pressure: float  # 0-1 scale (0=no defenders, 1=many defenders)
    game_state: str  # 'winning', 'losing', 'drawing'
    player_id: int
    timestamp: float  # Seconds from match start
    position: Tuple[float, float]  # (x, y) on pitch
    is_goal: bool = False  # Ground truth for training
    xg_value: float = 0.0  # Calculated xG
    confidence: float = 1.0


@dataclass
class XGReport:
    """xG analysis report for a match"""
    team1_xg: float
    team2_xg: float
    team1_shots: int
    team2_shots: int
    team1_shots_on_target: int
    team2_shots_on_target: int
    team1_conversion_rate: float  # Actual goals / xG
    team2_conversion_rate: float
    team1_shot_details: List[Dict]
    team2_shot_details: List[Dict]
    total_xg: float
    match_quality_score: float  # 0-1 scale based on shot quality
    confidence: float


class ExpectedGoalsModel:
    """
    Expected Goals (xG) model using ensemble of ML algorithms
    """

    def __init__(self):
        self.models = {}
        self.scaler = None
        self.is_trained = False
        self.feature_names = [
            'distance', 'angle', 'is_foot', 'is_head', 'is_penalty',
            'is_free_kick', 'is_counter', 'is_cross', 'is_through_ball',
            'defensive_pressure', 'is_winning', 'is_losing'
        ]

        # Rule-based baseline xG values (used when ML not available)
        self.baseline_xg = {
            'penalty': 0.79,
            'close_range': 0.35,  # < 6m
            'box': 0.12,  # 6-18m
            'edge_box': 0.06,  # 18-25m
            'long_range': 0.02,  # > 25m
            'header': 0.08,
            'free_kick': 0.05,
            'counter_attack': 1.5,  # Multiplier
        }

    def calculate_shot_features(self, shot: ShotEvent) -> Dict[str, float]:
        """
        Extract features from shot event
        """
        features = {
            'distance': shot.distance,
            'angle': shot.angle,
            'is_foot': 1.0 if shot.body_part == BodyPart.FOOT else 0.0,
            'is_head': 1.0 if shot.body_part == BodyPart.HEAD else 0.0,
            'is_penalty': 1.0 if shot.shot_type == ShotType.PENALTY else 0.0,
            'is_free_kick': 1.0 if shot.shot_type == ShotType.FREE_KICK else 0.0,
            'is_counter': 1.0 if shot.shot_type == ShotType.COUNTER_ATTACK else 0.0,
            'is_cross': 1.0 if shot.assist_type == AssistType.CROSS else 0.0,
            'is_through_ball': 1.0 if shot.assist_type == AssistType.THROUGH_BALL else 0.0,
            'defensive_pressure': shot.defensive_pressure,
            'is_winning': 1.0 if shot.game_state == 'winning' else 0.0,
            'is_losing': 1.0 if shot.game_state == 'losing' else 0.0,
        }
        return features

    def calculate_xg_rule_based(self, shot: ShotEvent) -> float:
        """
        Calculate xG using rule-based approach (fallback when ML not available)
        """
        # Start with base xG from distance
        if shot.shot_type == ShotType.PENALTY:
            xg = self.baseline_xg['penalty']
        elif shot.distance < 6:
            xg = self.baseline_xg['close_range']
        elif shot.distance < 18:
            xg = self.baseline_xg['box']
        elif shot.distance < 25:
            xg = self.baseline_xg['edge_box']
        else:
            xg = self.baseline_xg['long_range']

        # Adjust for angle (narrow angles are harder)
        angle_factor = np.sin(np.radians(shot.angle))
        xg *= angle_factor

        # Body part adjustments
        if shot.body_part == BodyPart.HEAD:
            xg *= 0.7  # Headers are harder

        # Shot type adjustments
        if shot.shot_type == ShotType.COUNTER_ATTACK:
            xg *= self.baseline_xg['counter_attack']
        elif shot.shot_type == ShotType.FREE_KICK:
            xg = self.baseline_xg['free_kick']

        # Assist type adjustments
        if shot.assist_type == AssistType.THROUGH_BALL:
            xg *= 1.3  # Through balls create better chances
        elif shot.assist_type == AssistType.CROSS:
            xg *= 0.9  # Crosses are harder to convert

        # Defensive pressure adjustment
        xg *= (1.0 - shot.defensive_pressure * 0.5)

        # Game state adjustment (losing teams shoot more desperately)
        if shot.game_state == 'losing':
            xg *= 0.9

        # Clamp to [0, 1]
        xg = max(0.0, min(1.0, xg))

        return xg

    def calculate_xg_ml(self, shot: ShotEvent) -> Tuple[float, float]:
        """
        Calculate xG using trained ML models (ensemble)
        Returns: (xg_value, confidence)
        """
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return self.calculate_xg_rule_based(shot), 0.6

        # Extract features
        features = self.calculate_shot_features(shot)
        X = np.array([[features[f] for f in self.feature_names]])

        # Scale features
        if self.scaler is not None:
            X = self.scaler.transform(X)

        # Ensemble prediction
        predictions = []
        weights = []

        if 'logistic' in self.models:
            pred = self.models['logistic'].predict_proba(X)[0][1]
            predictions.append(pred)
            weights.append(0.3)

        if 'random_forest' in self.models:
            pred = self.models['random_forest'].predict_proba(X)[0][1]
            predictions.append(pred)
            weights.append(0.35)

        if 'xgboost' in self.models and XGBOOST_AVAILABLE:
            pred = self.models['xgboost'].predict_proba(X)[0][1]
            predictions.append(pred)
            weights.append(0.35)

        # Weighted average
        if predictions:
            weights = np.array(weights) / sum(weights)
            xg = np.average(predictions, weights=weights)
            confidence = 0.85  # High confidence for ML models
        else:
            xg = self.calculate_xg_rule_based(shot)
            confidence = 0.6

        return float(xg), confidence

    def train(self, training_shots: List[ShotEvent]):
        """
        Train xG models on historical shot data
        """
        if not SKLEARN_AVAILABLE:
            print("⚠️  scikit-learn not available. Using rule-based xG only.")
            return

        if len(training_shots) < 100:
            print(f"⚠️  Need at least 100 shots for training (got {len(training_shots)})")
            return

        print(f"🎯 Training xG models on {len(training_shots)} shots...")

        # Prepare training data
        X = []
        y = []

        for shot in training_shots:
            features = self.calculate_shot_features(shot)
            X.append([features[f] for f in self.feature_names])
            y.append(1.0 if shot.is_goal else 0.0)

        X = np.array(X)
        y = np.array(y)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        self.scaler = StandardScaler()
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)

        # Train models
        print("   Training Logistic Regression...")
        self.models['logistic'] = LogisticRegression(random_state=42, max_iter=1000)
        self.models['logistic'].fit(X_train, y_train)

        print("   Training Random Forest...")
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42
        )
        self.models['random_forest'].fit(X_train, y_train)

        if XGBOOST_AVAILABLE:
            print("   Training XGBoost...")
            self.models['xgboost'] = xgb.XGBClassifier(
                n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
            )
            self.models['xgboost'].fit(X_train, y_train)

        # Evaluate
        print("\n📊 Model Performance:")
        for name, model in self.models.items():
            y_pred = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            print(f"   {name}: AUC-ROC = {auc:.3f}")

        self.is_trained = True
        print("✅ xG models trained successfully!")

    def calculate_xg(self, shot: ShotEvent) -> ShotEvent:
        """
        Calculate xG for a shot event
        """
        if SKLEARN_AVAILABLE and self.is_trained:
            xg, confidence = self.calculate_xg_ml(shot)
        else:
            xg = self.calculate_xg_rule_based(shot)
            confidence = 0.6

        shot.xg_value = xg
        shot.confidence = confidence
        return shot

    def analyze_match_xg(
        self,
        shots: List[ShotEvent],
        team1_id: int = 1,
        team2_id: int = 2
    ) -> XGReport:
        """
        Analyze xG for entire match
        """
        # Calculate xG for all shots
        shots_with_xg = [self.calculate_xg(shot) for shot in shots]

        # Split by team
        team1_shots = [s for s in shots_with_xg if s.player_id in range(1, 12)]
        team2_shots = [s for s in shots_with_xg if s.player_id in range(12, 23)]

        # Calculate team xG
        team1_xg = sum(s.xg_value for s in team1_shots)
        team2_xg = sum(s.xg_value for s in team2_shots)

        # Shots on target (xG > 0.1 as proxy)
        team1_sot = len([s for s in team1_shots if s.xg_value > 0.1])
        team2_sot = len([s for s in team2_shots if s.xg_value > 0.1])

        # Conversion rates (actual goals / expected goals)
        team1_goals = sum(1 for s in team1_shots if s.is_goal)
        team2_goals = sum(1 for s in team2_shots if s.is_goal)

        team1_conversion = team1_goals / team1_xg if team1_xg > 0 else 0.0
        team2_conversion = team2_goals / team2_xg if team2_xg > 0 else 0.0

        # Match quality score (average xG per shot)
        total_shots = len(shots_with_xg)
        avg_xg_per_shot = (team1_xg + team2_xg) / total_shots if total_shots > 0 else 0.0
        match_quality = min(1.0, avg_xg_per_shot * 10)  # Scale to 0-1

        # Shot details
        team1_details = [
            {
                'player_id': s.player_id,
                'timestamp': s.timestamp,
                'xg': round(s.xg_value, 3),
                'distance': round(s.distance, 1),
                'angle': round(s.angle, 1),
                'shot_type': s.shot_type.value,
                'body_part': s.body_part.value,
                'is_goal': s.is_goal
            }
            for s in sorted(team1_shots, key=lambda x: x.xg_value, reverse=True)
        ]

        team2_details = [
            {
                'player_id': s.player_id,
                'timestamp': s.timestamp,
                'xg': round(s.xg_value, 3),
                'distance': round(s.distance, 1),
                'angle': round(s.angle, 1),
                'shot_type': s.shot_type.value,
                'body_part': s.body_part.value,
                'is_goal': s.is_goal
            }
            for s in sorted(team2_shots, key=lambda x: x.xg_value, reverse=True)
        ]

        # Overall confidence
        avg_confidence = np.mean([s.confidence for s in shots_with_xg]) if shots_with_xg else 0.6

        return XGReport(
            team1_xg=round(team1_xg, 2),
            team2_xg=round(team2_xg, 2),
            team1_shots=len(team1_shots),
            team2_shots=len(team2_shots),
            team1_shots_on_target=team1_sot,
            team2_shots_on_target=team2_sot,
            team1_conversion_rate=round(team1_conversion, 2),
            team2_conversion_rate=round(team2_conversion, 2),
            team1_shot_details=team1_details,
            team2_shot_details=team2_details,
            total_xg=round(team1_xg + team2_xg, 2),
            match_quality_score=round(match_quality, 2),
            confidence=round(avg_confidence, 2)
        )

    def extract_shots_from_analytics(
        self,
        analytics: Dict,
        tracks: Dict,
        homography: Optional[np.ndarray] = None
    ) -> List[ShotEvent]:
        """
        Extract shot events from match analytics data
        """
        shots = []

        # Get shot events from analytics
        events = analytics.get('events', {})
        shot_events = events.get('shots', [])

        if not shot_events:
            # No shots detected - return empty list
            return shots

        # Process each shot
        for i, shot_data in enumerate(shot_events):
            # Extract shot details
            player_id = shot_data.get('player_id', 0)
            timestamp = shot_data.get('timestamp', 0.0)
            position = shot_data.get('position', (52.5, 34.0))  # Default center

            # Calculate distance and angle to goal
            goal_center = (105.0, 34.0)  # Assuming right goal
            distance = np.sqrt(
                (position[0] - goal_center[0]) ** 2 +
                (position[1] - goal_center[1]) ** 2
            )

            # Calculate angle to goal
            goal_width = 7.32
            goal_left = (105.0, 34.0 - goal_width / 2)
            goal_right = (105.0, 34.0 + goal_width / 2)

            angle_left = np.arctan2(goal_left[1] - position[1], goal_left[0] - position[0])
            angle_right = np.arctan2(goal_right[1] - position[1], goal_right[0] - position[0])
            angle = np.degrees(abs(angle_left - angle_right))

            # Infer shot type and body part (placeholder - need more analysis)
            shot_type = ShotType.OPEN_PLAY
            if distance > 25:
                shot_type = ShotType.FREE_KICK if np.random.random() > 0.7 else ShotType.OPEN_PLAY

            body_part = BodyPart.FOOT if distance < 15 else BodyPart.HEAD if np.random.random() > 0.7 else BodyPart.FOOT

            # Estimate defensive pressure (based on nearby opponent players)
            defensive_pressure = min(1.0, distance / 30.0)  # Placeholder

            # Determine game state (placeholder)
            game_state = 'drawing'

            shot = ShotEvent(
                distance=distance,
                angle=angle,
                body_part=body_part,
                shot_type=shot_type,
                assist_type=AssistType.PASS,
                defensive_pressure=defensive_pressure,
                game_state=game_state,
                player_id=player_id,
                timestamp=timestamp,
                position=position,
                is_goal=shot_data.get('is_goal', False)
            )

            shots.append(shot)

        return shots

    def export_xg_report(self, report: XGReport, output_path: str):
        """
        Export xG report to JSON file
        """
        report_dict = asdict(report)

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"✅ xG report saved to {output_path}")

    def print_xg_summary(self, report: XGReport):
        """
        Print human-readable xG summary
        """
        print("\n" + "="*60)
        print("⚽ EXPECTED GOALS (xG) ANALYSIS")
        print("="*60)

        print(f"\n📊 Match Overview:")
        print(f"   Total xG: {report.total_xg}")
        print(f"   Match Quality: {report.match_quality_score:.2f}/1.0")
        print(f"   Confidence: {report.confidence:.2f}")

        print(f"\n🔵 Team 1:")
        print(f"   xG: {report.team1_xg} ({report.team1_shots} shots)")
        print(f"   Shots on Target: {report.team1_shots_on_target}")
        print(f"   Conversion Rate: {report.team1_conversion_rate:.2f}x")

        print(f"\n🔴 Team 2:")
        print(f"   xG: {report.team2_xg} ({report.team2_shots} shots)")
        print(f"   Shots on Target: {report.team2_shots_on_target}")
        print(f"   Conversion Rate: {report.team2_conversion_rate:.2f}x")

        print(f"\n🎯 Top 3 Chances (Team 1):")
        for i, shot in enumerate(report.team1_shot_details[:3], 1):
            print(f"   {i}. Player #{shot['player_id']} - xG: {shot['xg']} "
                  f"({shot['distance']}m, {shot['angle']:.0f}°)")

        print(f"\n🎯 Top 3 Chances (Team 2):")
        for i, shot in enumerate(report.team2_shot_details[:3], 1):
            print(f"   {i}. Player #{shot['player_id']} - xG: {shot['xg']} "
                  f"({shot['distance']}m, {shot['angle']:.0f}°)")

        print("\n" + "="*60)


def main():
    """Demo xG calculation"""
    print("⚽ Expected Goals (xG) Model Demo\n")

    # Create model
    xg_model = ExpectedGoalsModel()

    # Demo shots
    demo_shots = [
        ShotEvent(
            distance=10.0, angle=45.0, body_part=BodyPart.FOOT,
            shot_type=ShotType.OPEN_PLAY, assist_type=AssistType.PASS,
            defensive_pressure=0.3, game_state='drawing',
            player_id=9, timestamp=450.0, position=(95.0, 34.0), is_goal=True
        ),
        ShotEvent(
            distance=6.0, angle=60.0, body_part=BodyPart.HEAD,
            shot_type=ShotType.CORNER, assist_type=AssistType.CROSS,
            defensive_pressure=0.7, game_state='losing',
            player_id=4, timestamp=1200.0, position=(99.0, 38.0), is_goal=False
        ),
        ShotEvent(
            distance=11.0, angle=90.0, body_part=BodyPart.FOOT,
            shot_type=ShotType.PENALTY, assist_type=AssistType.NONE,
            defensive_pressure=0.0, game_state='drawing',
            player_id=10, timestamp=2100.0, position=(94.0, 34.0), is_goal=True
        ),
    ]

    # Calculate xG
    print("📊 Calculating xG for demo shots...\n")
    report = xg_model.analyze_match_xg(demo_shots)

    # Print summary
    xg_model.print_xg_summary(report)


if __name__ == "__main__":
    main()
