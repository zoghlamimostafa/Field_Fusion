#!/usr/bin/env python3
"""
Metabolic Power Analyzer - Phase 2, Task 1
Tunisia Football AI Advanced Physical Analytics

Implements biomechanical metabolic power model based on:
- Osgnach et al. (2010): Energy cost model using equivalent slope
- di Prampero et al. (2005): Metabolic power calculation

Features:
- Metabolic power calculation (W/kg) from velocity and acceleration
- Energy expenditure tracking (kJ)
- High-intensity running distance
- Equivalent distance calculation
- Recovery time estimation based on energy depletion

References:
- Osgnach, C., et al. (2010). "Energy Cost and Metabolic Power in Elite Soccer"
- di Prampero, P.E., et al. (2005). "Sprint running: a new energetic approach"
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MetabolicPowerMetrics:
    """Results from metabolic power analysis"""
    player_id: int
    team: int

    # Energy metrics
    total_energy_expenditure: float  # kJ
    average_metabolic_power: float  # W/kg
    max_metabolic_power: float  # W/kg

    # High-intensity metrics
    high_intensity_distance: float  # meters (>20 W/kg)
    very_high_intensity_distance: float  # meters (>35 W/kg)
    elevated_power_distance: float  # meters (>25 W/kg)

    # Equivalent distance
    equivalent_distance: float  # meters (flat running equivalent)

    # Time-based metrics
    time_high_power: float  # seconds (>20 W/kg)
    time_very_high_power: float  # seconds (>35 W/kg)

    # Power distribution
    power_zone_times: Dict[str, float]  # seconds in each power zone

    # Fatigue estimation
    energy_depletion_percent: float  # 0-100%
    estimated_recovery_minutes: int

    # Frame tracking
    frames_analyzed: int
    minutes_played: float


class MetabolicPowerAnalyzer:
    """
    Calculate metabolic power and energy expenditure using validated biomechanical models

    The metabolic power approach considers both running velocity and acceleration,
    providing a more accurate estimate of energy expenditure than distance-based methods.

    Key Formula:
    P_met = E_c * v
    where:
    - P_met = metabolic power (W/kg)
    - E_c = energy cost of running (J/kg/m)
    - v = instantaneous velocity (m/s)

    Energy cost depends on equivalent slope (ES):
    ES = arctan(a_f / g)
    where a_f is forward acceleration and g is gravity (9.81 m/s²)
    """

    def __init__(self, fps: int = 25, player_mass: float = 75.0):
        """
        Initialize metabolic power analyzer

        Args:
            fps: Frames per second of tracking data
            player_mass: Average player mass in kg (for absolute power calculations)
        """
        self.fps = fps
        self.player_mass = player_mass
        self.gravity = 9.81  # m/s²

        # Constants from research
        self.energy_cost_flat = 3.6  # J/kg/m (energy cost on flat terrain)
        self.k_terrain = 155.4  # Terrain coefficient from di Prampero

        # Metabolic power thresholds (W/kg) - from Osgnach et al.
        self.power_zones = {
            'low': (0, 10),           # Light activity
            'moderate': (10, 20),      # Moderate intensity
            'high': (20, 35),          # High intensity
            'very_high': (35, 55),     # Very high intensity
            'maximal': (55, 200)       # Maximal/sprint
        }

        # High-intensity thresholds
        self.high_intensity_threshold = 20.0  # W/kg
        self.very_high_intensity_threshold = 35.0  # W/kg
        self.elevated_power_threshold = 25.5  # W/kg (common research threshold)

        # Energy capacity (typical values for elite athletes)
        self.max_energy_capacity = 2000.0  # kJ for 90 minutes

    def calculate_metabolic_power(self,
                                 velocities: np.ndarray,
                                 accelerations: np.ndarray) -> np.ndarray:
        """
        Calculate instantaneous metabolic power from velocity and acceleration

        Args:
            velocities: Array of velocities in m/s
            accelerations: Array of accelerations in m/s²

        Returns:
            Array of metabolic power values in W/kg
        """
        # Ensure arrays are numpy arrays
        velocities = np.asarray(velocities)
        accelerations = np.asarray(accelerations)

        # Calculate equivalent slope (ES)
        # ES = arctan(a_f / g)
        # where a_f is forward acceleration component
        equivalent_slopes = np.arctan(accelerations / self.gravity)

        # Calculate energy cost as function of equivalent slope
        # E_c = 155.4 * ES^5 - 30.4 * ES^4 - 43.3 * ES^3 + 46.3 * ES^2 + 19.5 * ES + 3.6
        # Simplified form from Osgnach et al.
        energy_costs = (
            self.k_terrain * equivalent_slopes**5
            - 30.4 * equivalent_slopes**4
            - 43.3 * equivalent_slopes**3
            + 46.3 * equivalent_slopes**2
            + 19.5 * equivalent_slopes
            + self.energy_cost_flat
        )

        # Ensure energy cost doesn't go below flat running
        energy_costs = np.maximum(energy_costs, self.energy_cost_flat)

        # Calculate metabolic power: P_met = E_c * v
        metabolic_power = energy_costs * velocities

        # Cap at reasonable maximum (professional sprinters ~70 W/kg)
        metabolic_power = np.minimum(metabolic_power, 75.0)

        return metabolic_power

    def calculate_energy_expenditure(self,
                                    metabolic_power: np.ndarray,
                                    time_step: float) -> float:
        """
        Calculate total energy expenditure from metabolic power time series

        Args:
            metabolic_power: Array of metabolic power values (W/kg)
            time_step: Time between measurements (seconds)

        Returns:
            Total energy expenditure in kJ
        """
        # Energy = Power * Time (W * s = J)
        # Convert to kJ and account for player mass
        energy_joules = np.sum(metabolic_power * self.player_mass * time_step)
        energy_kj = energy_joules / 1000.0

        return energy_kj

    def calculate_equivalent_distance(self,
                                     velocities: np.ndarray,
                                     metabolic_power: np.ndarray,
                                     time_step: float) -> float:
        """
        Calculate equivalent distance on flat terrain

        This is the distance that would result in the same energy expenditure
        if running on flat ground at constant speed.

        Args:
            velocities: Array of velocities (m/s)
            metabolic_power: Array of metabolic power (W/kg)
            time_step: Time between measurements (seconds)

        Returns:
            Equivalent distance in meters
        """
        # Total energy expenditure
        total_energy = np.sum(metabolic_power * time_step)  # J/kg

        # Equivalent distance = Total energy / Energy cost of flat running
        equivalent_distance = total_energy / self.energy_cost_flat

        return equivalent_distance

    def analyze_player(self,
                      velocities: List[float],
                      accelerations: List[float],
                      player_id: int,
                      team: int) -> MetabolicPowerMetrics:
        """
        Complete metabolic power analysis for a single player

        Args:
            velocities: List of velocities in m/s
            accelerations: List of accelerations in m/s²
            player_id: Player identifier
            team: Team identifier

        Returns:
            MetabolicPowerMetrics object with all calculated metrics
        """
        if len(velocities) == 0 or len(accelerations) == 0:
            # Return empty metrics
            return self._empty_metrics(player_id, team)

        # Convert to numpy arrays
        velocities = np.array(velocities)
        accelerations = np.array(accelerations)

        # Ensure same length
        min_length = min(len(velocities), len(accelerations))
        velocities = velocities[:min_length]
        accelerations = accelerations[:min_length]

        # Calculate metabolic power
        metabolic_power = self.calculate_metabolic_power(velocities, accelerations)

        # Time step between measurements
        time_step = 1.0 / self.fps

        # Calculate energy expenditure
        total_energy = self.calculate_energy_expenditure(metabolic_power, time_step)

        # Calculate equivalent distance
        equivalent_distance = self.calculate_equivalent_distance(
            velocities, metabolic_power, time_step
        )

        # Power statistics
        avg_power = np.mean(metabolic_power)
        max_power = np.max(metabolic_power)

        # High-intensity distances
        high_intensity_mask = metabolic_power >= self.high_intensity_threshold
        very_high_intensity_mask = metabolic_power >= self.very_high_intensity_threshold
        elevated_power_mask = metabolic_power >= self.elevated_power_threshold

        high_intensity_distance = np.sum(velocities[high_intensity_mask] * time_step)
        very_high_intensity_distance = np.sum(velocities[very_high_intensity_mask] * time_step)
        elevated_power_distance = np.sum(velocities[elevated_power_mask] * time_step)

        # Time at high power
        time_high_power = np.sum(high_intensity_mask) * time_step
        time_very_high_power = np.sum(very_high_intensity_mask) * time_step

        # Power zone distribution
        power_zone_times = self._calculate_power_zones(metabolic_power, time_step)

        # Fatigue estimation
        energy_depletion = min((total_energy / self.max_energy_capacity) * 100, 100.0)
        recovery_minutes = self._estimate_recovery(total_energy, energy_depletion)

        # Frame tracking
        frames_analyzed = len(velocities)
        minutes_played = frames_analyzed / (self.fps * 60)

        return MetabolicPowerMetrics(
            player_id=player_id,
            team=team,
            total_energy_expenditure=total_energy,
            average_metabolic_power=avg_power,
            max_metabolic_power=max_power,
            high_intensity_distance=high_intensity_distance,
            very_high_intensity_distance=very_high_intensity_distance,
            elevated_power_distance=elevated_power_distance,
            equivalent_distance=equivalent_distance,
            time_high_power=time_high_power,
            time_very_high_power=time_very_high_power,
            power_zone_times=power_zone_times,
            energy_depletion_percent=energy_depletion,
            estimated_recovery_minutes=recovery_minutes,
            frames_analyzed=frames_analyzed,
            minutes_played=minutes_played
        )

    def _calculate_power_zones(self,
                               metabolic_power: np.ndarray,
                               time_step: float) -> Dict[str, float]:
        """Calculate time spent in each power zone"""
        zone_times = {}

        for zone_name, (min_power, max_power) in self.power_zones.items():
            mask = (metabolic_power >= min_power) & (metabolic_power < max_power)
            zone_times[zone_name] = np.sum(mask) * time_step

        return zone_times

    def _estimate_recovery(self, total_energy: float, energy_depletion: float) -> int:
        """
        Estimate recovery time based on energy expenditure

        Recovery rate is typically ~30-50 kJ per hour for passive recovery
        """
        recovery_rate_per_hour = 40.0  # kJ/hour (conservative estimate)

        # Recovery time in hours
        recovery_hours = total_energy / recovery_rate_per_hour

        # Convert to minutes, with minimum of 30 minutes
        recovery_minutes = max(int(recovery_hours * 60), 30)

        # Cap at 240 minutes (4 hours)
        recovery_minutes = min(recovery_minutes, 240)

        return recovery_minutes

    def _empty_metrics(self, player_id: int, team: int) -> MetabolicPowerMetrics:
        """Return empty metrics for players with no data"""
        return MetabolicPowerMetrics(
            player_id=player_id,
            team=team,
            total_energy_expenditure=0.0,
            average_metabolic_power=0.0,
            max_metabolic_power=0.0,
            high_intensity_distance=0.0,
            very_high_intensity_distance=0.0,
            elevated_power_distance=0.0,
            equivalent_distance=0.0,
            time_high_power=0.0,
            time_very_high_power=0.0,
            power_zone_times={zone: 0.0 for zone in self.power_zones.keys()},
            energy_depletion_percent=0.0,
            estimated_recovery_minutes=0,
            frames_analyzed=0,
            minutes_played=0.0
        )

    def export_metrics(self, metrics: MetabolicPowerMetrics) -> Dict:
        """Export metrics to dictionary format for JSON/API"""
        return {
            'player_id': metrics.player_id,
            'team': metrics.team,
            'energy_metrics': {
                'total_expenditure_kj': round(metrics.total_energy_expenditure, 2),
                'average_power_wkg': round(metrics.average_metabolic_power, 2),
                'max_power_wkg': round(metrics.max_metabolic_power, 2),
                'energy_depletion_percent': round(metrics.energy_depletion_percent, 1)
            },
            'high_intensity_metrics': {
                'high_intensity_distance_m': round(metrics.high_intensity_distance, 1),
                'very_high_intensity_distance_m': round(metrics.very_high_intensity_distance, 1),
                'elevated_power_distance_m': round(metrics.elevated_power_distance, 1),
                'time_high_power_s': round(metrics.time_high_power, 1),
                'time_very_high_power_s': round(metrics.time_very_high_power, 1)
            },
            'equivalent_distance_m': round(metrics.equivalent_distance, 1),
            'power_zones_seconds': {
                zone: round(time_s, 1)
                for zone, time_s in metrics.power_zone_times.items()
            },
            'recovery_needed_minutes': metrics.estimated_recovery_minutes,
            'tracking': {
                'frames_analyzed': metrics.frames_analyzed,
                'minutes_played': round(metrics.minutes_played, 2)
            }
        }

    def batch_export(self, metrics_list: List[MetabolicPowerMetrics]) -> Dict:
        """Export batch of player metrics with team summaries"""
        players_data = [self.export_metrics(m) for m in metrics_list]

        # Calculate team summaries
        team_summaries = defaultdict(lambda: {
            'total_energy': 0.0,
            'avg_power': [],
            'player_count': 0
        })

        for metrics in metrics_list:
            team_summaries[metrics.team]['total_energy'] += metrics.total_energy_expenditure
            team_summaries[metrics.team]['avg_power'].append(metrics.average_metabolic_power)
            team_summaries[metrics.team]['player_count'] += 1

        # Format team summaries
        formatted_summaries = {}
        for team, data in team_summaries.items():
            formatted_summaries[f'team_{team}'] = {
                'total_energy_kj': round(data['total_energy'], 2),
                'average_power_wkg': round(np.mean(data['avg_power']), 2),
                'player_count': data['player_count']
            }

        return {
            'players': players_data,
            'team_summaries': formatted_summaries,
            'total_players': len(metrics_list)
        }


def calculate_velocity_acceleration_from_trajectory(
    trajectory: List[Tuple[float, float, int]],
    fps: int,
    pitch_length: float = 105.0,
    pitch_width: float = 68.0
) -> Tuple[List[float], List[float]]:
    """
    Helper function to calculate velocities and accelerations from trajectory

    Args:
        trajectory: List of (x, y, frame) tuples in field coordinates (meters)
        fps: Frames per second
        pitch_length: Pitch length in meters
        pitch_width: Pitch width in meters

    Returns:
        Tuple of (velocities, accelerations) in m/s and m/s²
    """
    if len(trajectory) < 2:
        return [], []

    velocities = []
    positions = []

    # Calculate velocities
    for i in range(1, len(trajectory)):
        x1, y1, frame1 = trajectory[i-1]
        x2, y2, frame2 = trajectory[i]

        # Distance in meters
        distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # Time in seconds
        time_delta = (frame2 - frame1) / fps

        if time_delta > 0:
            velocity = distance / time_delta
            velocities.append(velocity)
        else:
            velocities.append(0.0)

    # Calculate accelerations from velocities
    accelerations = []
    time_step = 1.0 / fps

    for i in range(1, len(velocities)):
        accel = (velocities[i] - velocities[i-1]) / time_step
        accelerations.append(accel)

    # Pad to same length as velocities
    if accelerations:
        accelerations.insert(0, accelerations[0])  # Duplicate first value

    return velocities, accelerations


if __name__ == "__main__":
    """Demo: Calculate metabolic power for sample player"""
    print("=" * 60)
    print("Metabolic Power Analyzer Demo")
    print("=" * 60)

    # Create analyzer
    analyzer = MetabolicPowerAnalyzer(fps=25, player_mass=75.0)

    # Simulate player data: 45 minutes of activity
    np.random.seed(42)
    num_frames = 25 * 60 * 45  # 45 minutes at 25 fps

    # Simulate realistic velocity profile (mixture of walking, jogging, running, sprinting)
    velocities = np.random.choice(
        [1.0, 2.5, 4.0, 6.5, 8.0],  # m/s (walking to sprinting)
        size=num_frames,
        p=[0.3, 0.3, 0.2, 0.15, 0.05]  # Probability distribution
    )

    # Add some noise
    velocities += np.random.normal(0, 0.5, num_frames)
    velocities = np.clip(velocities, 0, 11.0)  # Cap at ~40 km/h

    # Calculate accelerations (change in velocity)
    accelerations = np.diff(velocities, prepend=velocities[0]) * 25  # fps = 25
    accelerations = np.clip(accelerations, -4.0, 4.0)  # Realistic acceleration limits

    # Analyze player
    print("\nAnalyzing player data...")
    metrics = analyzer.analyze_player(
        velocities=velocities.tolist(),
        accelerations=accelerations.tolist(),
        player_id=10,
        team=1
    )

    # Display results
    print(f"\n{'Player Metrics':^60}")
    print("=" * 60)
    print(f"Player ID: {metrics.player_id}")
    print(f"Minutes Played: {metrics.minutes_played:.1f}")
    print()
    print("Energy Metrics:")
    print(f"  Total Energy Expenditure: {metrics.total_energy_expenditure:.1f} kJ")
    print(f"  Average Metabolic Power: {metrics.average_metabolic_power:.1f} W/kg")
    print(f"  Max Metabolic Power: {metrics.max_metabolic_power:.1f} W/kg")
    print(f"  Energy Depletion: {metrics.energy_depletion_percent:.1f}%")
    print()
    print("High-Intensity Metrics:")
    print(f"  HI Distance (>20 W/kg): {metrics.high_intensity_distance:.1f} m")
    print(f"  Very HI Distance (>35 W/kg): {metrics.very_high_intensity_distance:.1f} m")
    print(f"  Time at High Power: {metrics.time_high_power:.1f} s")
    print()
    print(f"Equivalent Distance: {metrics.equivalent_distance:.1f} m")
    print(f"Recovery Needed: {metrics.estimated_recovery_minutes} minutes")
    print()
    print("Power Zone Distribution (seconds):")
    for zone, time_s in metrics.power_zone_times.items():
        print(f"  {zone.capitalize():15s}: {time_s:>7.1f} s")

    # Export to JSON format
    print("\n" + "=" * 60)
    print("JSON Export Sample:")
    print("=" * 60)
    import json
    exported = analyzer.export_metrics(metrics)
    print(json.dumps(exported, indent=2))

    print("\n✅ Metabolic power analysis complete!")
