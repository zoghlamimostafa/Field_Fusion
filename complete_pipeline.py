#!/usr/bin/env python3
"""
Complete Football Analysis Pipeline - Level 4 Elite SaaS
Integrates ALL features: detection, tracking, events, heatmaps, analytics,
formation detection, fatigue analysis, pressing metrics, pass networks, alerts, confidence scoring,
xG model, player valuation, injury risk prediction, opposition scouting

🇹🇳 TUNISIA FOOTBALL AI - Elite Level 4 SaaS Platform
"""

import numpy as np
from trackers.football_tracker import FootballTracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from pitch_detector import PitchDetector
from speed_distance_estimator import SpeedDistanceEstimator
from heatmap_generator import HeatmapGenerator
from event_detector import EventDetector
from analytics_exporter import AnalyticsExporter
from player_id_consolidator import PlayerIDConsolidator

# Level 3 Intelligence Modules
from pitch_calibrator_enhanced import EnhancedPitchCalibrator
from fatigue_estimator import FatigueEstimator
from formation_detector import FormationDetector
from alert_engine import AlertEngine
from pressing_analyzer import PressingAnalyzer
from pass_network_analyzer import PassNetworkAnalyzer
from confidence_scorer import ConfidenceScorer
from pdf_report_exporter import PDFReportExporter

# Level 4 Advanced Analytics Modules
from xg_model import ExpectedGoalsModel
from player_valuation import PlayerValuationModel, PlayerProfile, Position, League
from injury_risk_model import InjuryRiskModel
from opposition_scouting import OppositionScoutingSystem

# NEW: Jersey Number Recognition
from jersey_number_recognizer import JerseyNumberRecognizer

from utils import read_video, save_video
import os
import json

def main():
    print("=" * 80)
    print("🇹🇳 TUNISIA FOOTBALL AI - LEVEL 4 ELITE SAAS PLATFORM")
    print("=" * 80)

    # Configuration
    video_path = 'input_videos/08fd33_4.mp4'
    use_football_model = True
    video_fps = 25

    # Read video
    print("\n📹 Step 1: Reading video...")
    video_frames = read_video(video_path)
    print(f"   ✅ Loaded {len(video_frames)} frames")

    # Initialize ALL components (Basic + Level 3)
    print("\n🔧 Step 2: Initializing AI components...")
    # Basic components
    tracker = FootballTracker(model_path=None, use_football_model=use_football_model)
    pitch_detector = PitchDetector()
    speed_estimator = SpeedDistanceEstimator(fps=video_fps)
    heatmap_gen = HeatmapGenerator()
    event_detector = EventDetector()
    exporter = AnalyticsExporter()
    from camera_movement_estimator import CameraMovementEstimator
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])

    # Level 3 Intelligence Components
    enhanced_pitch_calibrator = EnhancedPitchCalibrator()
    fatigue_estimator = FatigueEstimator(fps=video_fps)
    formation_detector = FormationDetector(fps=video_fps)
    alert_engine = AlertEngine(fps=video_fps)
    pressing_analyzer = PressingAnalyzer(fps=video_fps)
    pass_network_analyzer = PassNetworkAnalyzer(fps=video_fps)
    confidence_scorer = ConfidenceScorer(fps=video_fps)
    pdf_exporter = PDFReportExporter()

    # Level 4 Advanced Analytics Components
    xg_model = ExpectedGoalsModel()
    valuation_model = PlayerValuationModel()
    injury_risk_model = InjuryRiskModel()
    opposition_scout = OppositionScoutingSystem()

    # NEW: Jersey Number Recognition
    jersey_recognizer = JerseyNumberRecognizer(min_confidence=0.5)

    print("   ✅ All components initialized (Basic + Level 3 + Level 4 + Jersey Recognition)")

    # Detect and track objects
    print("\n🎯 Step 3: Detecting and tracking players, ball, referees...")
    tracks = tracker.get_object_tracks(
        video_frames,
        read_from_stub=False,
        stub_path='stubs/track_stubs_complete.pkl'
    )

    print(f"   ✅ Players: {sum(len(frame) for frame in tracks['players'])} detections")
    print(f"   ✅ Goalkeepers: {sum(len(frame) for frame in tracks['goalkeepers'])} detections")
    print(f"   ✅ Referees: {sum(len(frame) for frame in tracks['referees'])} detections")
    print(f"   ✅ Ball: {sum(len(frame) for frame in tracks['ball'])} detections")

    # Interpolate ball positions
    print("\n⚽ Step 4: Interpolating ball positions...")
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])
    print("   ✅ Ball tracking smoothed")

    # Consolidate fragmented player IDs
    print("\n🔗 Step 5: Consolidating player IDs...")
    consolidator = PlayerIDConsolidator(expected_players_per_team=11)
    id_mapping = consolidator.consolidate_player_ids(tracks)
    tracks = consolidator.apply_consolidation(tracks, id_mapping)
    print("   ✅ Player IDs consolidated to actual players")

    # NEW: Jersey Number Recognition
    print("\n🔢 Step 5a: Jersey Number Recognition (OCR)...")
    jersey_numbers = jersey_recognizer.detect_numbers_in_tracks(
        video_frames, tracks, sample_every_n_frames=25
    )
    if jersey_numbers:
        tracks = jersey_recognizer.assign_numbers_to_tracks(tracks, jersey_numbers)
        jersey_recognizer.export_number_mapping('outputs/jersey_numbers.json')
    else:
        print("   ⚠️  No jersey numbers detected")

    # Add position tracking
    print("\n📍 Step 6: Adding position tracking...")
    tracker.add_position_to_tracks(tracks)
    print("   ✅ Positions tracked")

    # Compensate for camera movement
    print("\n🎥 Step 7: Camera movement compensation...")
    camera_stub_path = 'stubs/camera_movement_complete.pkl'
    camera_movement = camera_movement_estimator.get_camera_movement(
        video_frames,
        read_from_stub=os.path.exists(camera_stub_path),
        stub_path=camera_stub_path,
    )
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement)
    print("   ✅ Camera movement compensated")

    # Detect pitch and estimate homography (ENHANCED)
    print("\n🏟️  Step 8: Enhanced Pitch Calibration...")
    try:
        # Try enhanced calibration first
        homography, calibration_info = enhanced_pitch_calibrator.calibrate_multi_frame(
            video_frames,
            frame_indices=[0, 100, 250, 500, 750],
            min_confidence=0.5
        )

        if homography is not None and calibration_info.get('confidence', 0) > 0.5:
            print(f"   ✅ Enhanced homography: {calibration_info['method']}, "
                  f"confidence={calibration_info['confidence']:.2f}")
        else:
            # Fallback to basic calibration
            print("   ⚠️  Enhanced calibration failed, trying basic method...")
            homography, calibration_info = pitch_detector.estimate_homography_auto(
                video_frames[0],
                video_path=video_path,
                return_metadata=True,
            )
            if homography is not None:
                print(f"   ✅ Basic homography estimated ({calibration_info.get('method', 'unknown')})")
            else:
                print("   ⚠️  Using fallback homography")
                calibration_info = {'method': 'fallback', 'confidence': 0.3}
    except Exception as e:
        print(f"   ⚠️  Calibration error: {e}")
        homography = None
        calibration_info = {'method': 'error', 'confidence': 0.0}

    # Assign teams
    print("\n👕 Step 9: Team assignment...")
    team_assigner = TeamAssigner()
    team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

    for frame_num, player_track in enumerate(tracks['players']):
        for player_id, track in player_track.items():
            team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
            tracks['players'][frame_num][player_id]['team'] = team
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]

    print("   ✅ Teams assigned")

    # Assign ball possession
    print("\n🏐 Step 10: Ball possession analysis...")
    player_assigner = PlayerBallAssigner()
    team_ball_control = []

    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
        else:
            team_ball_control.append(team_ball_control[-1] if team_ball_control else 0)

    team_ball_control = np.array(team_ball_control)
    print("   ✅ Possession calculated")

    # Calculate speed and distance
    print("\n⚡ Step 11: Speed and distance estimation...")
    total_distance, max_speed, avg_speed = speed_estimator.add_speed_and_distance_to_tracks(
        tracks, homography
    )
    print(f"   ✅ Calculated metrics for {len(total_distance)} players")

    # Detect events
    print("\n🎬 Step 12: Event detection...")
    passes = event_detector.detect_passes(tracks, tracks['ball'])
    shots = event_detector.detect_shots(tracks, tracks['ball'])
    interceptions = event_detector.detect_interceptions(tracks, passes)

    print(f"   ✅ Passes: {len(passes)}")
    print(f"   ✅ Shots: {len(shots)}")
    print(f"   ✅ Interceptions: {len(interceptions)}")

    # Generate heatmaps
    print("\n🔥 Step 13: Generating heatmaps...")
    os.makedirs('outputs/heatmaps', exist_ok=True)
    heatmaps = heatmap_gen.generate_all_heatmaps(tracks, homography)
    print(f"   ✅ Generated {len(heatmaps)} heatmaps")

    # Export analytics
    print("\n📊 Step 14: Exporting basic analytics...")
    analytics = exporter.export_all(
        tracks, total_distance, max_speed, avg_speed,
        team_ball_control, passes, shots, interceptions
    )

    # === NEW LEVEL 3 INTELLIGENCE ANALYSIS ===

    # Step 15: Formation Detection
    print("\n⚽ Step 15: Formation Detection...")
    formations = formation_detector.detect_formations(
        tracks,
        homography=homography,
        sample_frames=10
    )

    # Step 16: Fatigue Analysis
    print("\n💪 Step 16: Fatigue Analysis...")
    fatigue_data = fatigue_estimator.estimate_fatigue(
        tracks,
        analytics,
        homography=homography
    )

    # Step 17: Pressing Analysis
    print("\n🛡️  Step 17: Pressing Analysis...")
    pressing_data = pressing_analyzer.analyze_pressing(
        tracks,
        analytics,
        formations=formations,
        homography=homography
    )

    # Step 18: Pass Network Analysis
    print("\n🔗 Step 18: Pass Network Analysis...")
    pass_networks = pass_network_analyzer.analyze_pass_networks(
        analytics,
        tracks=tracks
    )

    # Step 19: Alert Generation
    print("\n🚨 Step 19: Generating Tactical Alerts...")
    alerts = alert_engine.generate_alerts(
        tracks,
        analytics,
        formations=formations,
        fatigue_data=fatigue_data
    )

    # Step 20: Confidence Scoring
    print("\n📊 Step 20: Calculating Confidence Scores...")
    confidence_score = confidence_scorer.calculate_confidence(
        tracks,
        analytics,
        calibration_info,
        formations=formations,
        fatigue_data=fatigue_data,
        pressing_data=pressing_data
    )

    # === NEW LEVEL 4 ADVANCED ANALYTICS ===

    # Step 21: Expected Goals (xG) Analysis
    print("\n⚽ Step 21: Expected Goals (xG) Analysis...")
    xg_shots = xg_model.extract_shots_from_analytics(analytics, tracks, homography)
    if xg_shots:
        xg_report = xg_model.analyze_match_xg(xg_shots)
        xg_model.print_xg_summary(xg_report)
    else:
        print("   ⚠️  No shots detected for xG analysis")
        xg_report = None

    # Step 22: Player Transfer Valuation
    print("\n💰 Step 22: Player Transfer Valuation...")
    valuation_reports = {}
    player_stats_list = analytics.get('player_stats', [])

    # Value top 3 players from each team
    team1_players = [p for p in player_stats_list if p.get('team') == 1]
    team2_players = [p for p in player_stats_list if p.get('team') == 2]

    top_team1 = sorted(team1_players, key=lambda x: x.get('total_distance_m', 0), reverse=True)[:3]
    top_team2 = sorted(team2_players, key=lambda x: x.get('total_distance_m', 0), reverse=True)[:3]

    for player_data in top_team1 + top_team2:
        player_id = player_data['player_id']
        profile = valuation_model.create_profile_from_analytics(
            player_id, analytics, fatigue_data,
            age=25.0, position=Position.MIDFIELDER, league=League.SECOND_TIER,
            name=f"Player_{player_id}"
        )
        val_report = valuation_model.estimate_value(profile)
        valuation_reports[player_id] = val_report

    print(f"   ✅ Valued {len(valuation_reports)} key players")

    # Step 23: Injury Risk Assessment
    print("\n🏥 Step 23: Injury Risk Assessment...")
    injury_profiles = []

    for player_data in player_stats_list:
        player_id = player_data['player_id']
        profile = injury_risk_model.create_profile_from_fatigue_data(
            player_id, fatigue_data, analytics,
            name=f"Player_{player_id}", age=25.0, position="midfielder"
        )
        injury_profiles.append(profile)

    if injury_profiles:
        injury_report_team1 = injury_risk_model.generate_team_report(
            [p for p in injury_profiles if p.player_id in range(1, 12)], team_id=1
        )
        injury_report_team2 = injury_risk_model.generate_team_report(
            [p for p in injury_profiles if p.player_id in range(12, 23)], team_id=2
        )
        injury_risk_model.print_report_summary(injury_report_team1)
        injury_risk_model.print_report_summary(injury_report_team2)
    else:
        print("   ⚠️  No injury risk data available")
        injury_report_team1 = None
        injury_report_team2 = None

    # Step 24: Opposition Scouting (for Team 2)
    print("\n🔍 Step 24: Opposition Scouting (Team 2)...")
    opposition_report = opposition_scout.generate_opposition_report(
        analytics, formations, pressing_data, pass_networks, fatigue_data,
        team_id=2, team_name="Opposition Team"
    )
    opposition_scout.print_report_summary(opposition_report)

    # Consolidate all Level 3 + Level 4 analytics
    print("\n📦 Consolidating Level 3 + Level 4 Analytics...")
    level3_analytics = {
        'formations': formation_detector.export_formations(formations) if formations else {},
        'fatigue': fatigue_estimator.export_fatigue_data(fatigue_data) if fatigue_data else {},
        'pressing': pressing_analyzer.export_pressing_data(pressing_data) if pressing_data else {},
        'pass_networks': pass_network_analyzer.export_pass_network_data(pass_networks) if pass_networks else {},
        'alerts': alert_engine.export_alerts_to_dict(alerts) if alerts else {},
        'confidence': confidence_scorer.export_confidence_data(confidence_score)
    }

    # Level 4 analytics
    from dataclasses import asdict
    level4_analytics = {
        'xg_analysis': asdict(xg_report) if xg_report else {},
        'player_valuations': {
            pid: asdict(report) for pid, report in valuation_reports.items()
        },
        'injury_risk_team1': asdict(injury_report_team1) if injury_report_team1 else {},
        'injury_risk_team2': asdict(injury_report_team2) if injury_report_team2 else {},
        'opposition_scouting': asdict(opposition_report) if opposition_report else {}
    }

    json_safe_level3 = exporter._to_jsonable(level3_analytics)
    json_safe_level4 = exporter._to_jsonable(level4_analytics)

    # Save Level 3 analytics to JSON
    os.makedirs('outputs/level3_reports', exist_ok=True)
    with open('outputs/level3_reports/formations.json', 'w') as f:
        json.dump(json_safe_level3['formations'], f, indent=2)
    with open('outputs/level3_reports/fatigue.json', 'w') as f:
        json.dump(json_safe_level3['fatigue'], f, indent=2)
    with open('outputs/level3_reports/pressing.json', 'w') as f:
        json.dump(json_safe_level3['pressing'], f, indent=2)
    with open('outputs/level3_reports/pass_networks.json', 'w') as f:
        json.dump(json_safe_level3['pass_networks'], f, indent=2)
    with open('outputs/level3_reports/alerts.json', 'w') as f:
        json.dump(json_safe_level3['alerts'], f, indent=2)
    with open('outputs/level3_reports/confidence.json', 'w') as f:
        json.dump(json_safe_level3['confidence'], f, indent=2)
    pdf_paths = pdf_exporter.export_report_dicts(json_safe_level3, 'outputs/level3_reports')
    print(f"   ✅ Level 3 analytics saved ({len(pdf_paths)} PDFs)")

    # Save Level 4 analytics to JSON
    os.makedirs('outputs/level4_reports', exist_ok=True)
    with open('outputs/level4_reports/xg_analysis.json', 'w') as f:
        json.dump(json_safe_level4['xg_analysis'], f, indent=2)
    with open('outputs/level4_reports/player_valuations.json', 'w') as f:
        json.dump(json_safe_level4['player_valuations'], f, indent=2)
    with open('outputs/level4_reports/injury_risk_team1.json', 'w') as f:
        json.dump(json_safe_level4['injury_risk_team1'], f, indent=2)
    with open('outputs/level4_reports/injury_risk_team2.json', 'w') as f:
        json.dump(json_safe_level4['injury_risk_team2'], f, indent=2)
    with open('outputs/level4_reports/opposition_scouting.json', 'w') as f:
        json.dump(json_safe_level4['opposition_scouting'], f, indent=2)
    print(f"   ✅ Level 4 analytics saved (5 JSON files)")

    # Draw annotations
    print("\n🎨 Step 25: Rendering output video...")
    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)

    # Save output
    output_path = 'output_videos/complete_analysis_level4.avi'
    save_video(output_video_frames, output_path)
    print(f"   ✅ Saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("📈 LEVEL 4 ELITE ANALYSIS SUMMARY")
    print("=" * 80)

    print("\n🏆 Team Statistics:")
    team_stats = analytics['team_stats']
    print(f"   Team 1: {team_stats['team_1']['possession_percent']:.1f}% possession, "
          f"{team_stats['team_1']['total_passes']} passes, "
          f"{team_stats['team_1']['total_shots']} shots")
    print(f"   Team 2: {team_stats['team_2']['possession_percent']:.1f}% possession, "
          f"{team_stats['team_2']['total_passes']} passes, "
          f"{team_stats['team_2']['total_shots']} shots")

    print("\n👟 Top 5 Players by Distance:")
    player_stats = analytics['player_stats']
    for i, player in enumerate(player_stats[:5], 1):
        print(f"   {i}. Player {player['player_id']} (Team {player['team']}): "
              f"{player['total_distance_m']:.1f}m, "
              f"Max speed: {player['max_speed_kmh']:.1f} km/h")

    print("\n⚡ Top 5 Players by Speed:")
    sorted_by_speed = sorted(player_stats, key=lambda x: x['max_speed_kmh'], reverse=True)
    for i, player in enumerate(sorted_by_speed[:5], 1):
        print(f"   {i}. Player {player['player_id']} (Team {player['team']}): "
              f"{player['max_speed_kmh']:.1f} km/h")

    # Print Level 3 summaries
    if formations:
        print("\n" + formation_detector.generate_formation_summary(formations))

    if fatigue_data:
        print(fatigue_estimator.generate_fatigue_summary(fatigue_data))

    if pressing_data:
        print(pressing_analyzer.generate_pressing_summary(pressing_data))

    if pass_networks:
        print(pass_network_analyzer.generate_pass_network_summary(pass_networks))

    if alerts:
        print(alert_engine.generate_alert_summary(alerts))

    if confidence_score:
        print(confidence_scorer.generate_confidence_summary(confidence_score))

    print("\n📁 Output Files:")
    print(f"   📹 Video: {output_path}")
    print(f"   📊 HTML Report: {analytics['html_report']}")
    print(f"\n   Basic Analytics:")
    print(f"      📄 Player Stats: outputs/reports/player_stats.json")
    print(f"      📄 Team Stats: outputs/reports/team_stats.json")
    print(f"      📄 Events: outputs/reports/events.json")
    print(f"      🔥 Heatmaps: outputs/heatmaps/")
    print(f"\n   Level 3 Intelligence:")
    print(f"      ⚽ Formations: outputs/level3_reports/formations.json")
    print(f"      💪 Fatigue: outputs/level3_reports/fatigue.json")
    print(f"      🛡️  Pressing: outputs/level3_reports/pressing.json")
    print(f"      🔗 Pass Networks: outputs/level3_reports/pass_networks.json")
    print(f"      🚨 Alerts: outputs/level3_reports/alerts.json")
    print(f"      📊 Confidence: outputs/level3_reports/confidence.json")
    print(f"\n   Level 4 Advanced Analytics:")
    print(f"      ⚽ xG Analysis: outputs/level4_reports/xg_analysis.json")
    print(f"      💰 Player Valuations: outputs/level4_reports/player_valuations.json")
    print(f"      🏥 Injury Risk Team 1: outputs/level4_reports/injury_risk_team1.json")
    print(f"      🏥 Injury Risk Team 2: outputs/level4_reports/injury_risk_team2.json")
    print(f"      🔍 Opposition Scouting: outputs/level4_reports/opposition_scouting.json")

    print("\n" + "=" * 80)
    print("✅ LEVEL 4 ELITE SAAS PIPELINE COMPLETE!")
    print("=" * 80)

if __name__ == '__main__':
    main()
