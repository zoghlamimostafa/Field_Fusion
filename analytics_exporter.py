import json
import csv
import pandas as pd
import os
from datetime import datetime
import numpy as np

class AnalyticsExporter:
    """
    Export analytics data to JSON, CSV, and HTML reports
    """
    def __init__(self, output_dir='outputs/reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _to_jsonable(self, value):
        """Recursively convert NumPy values to native Python types with string keys."""
        if isinstance(value, dict):
            # Ensure all dict keys are strings for JSON/Gradio compatibility
            return {str(self._to_jsonable(key)): self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._to_jsonable(item) for item in value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def export_player_stats(self, tracks, total_distance, max_speed, avg_speed, filename='player_stats'):
        """
        Export individual player statistics
        """
        # Prepare data
        stats_list = []

        for player_id in total_distance.keys():
            # Get player team and jersey number
            team = None
            jersey_number = None
            for frame_tracks in tracks.get('players', []):
                if player_id in frame_tracks:
                    team = frame_tracks[player_id].get('team')
                    jersey_number = frame_tracks[player_id].get('jersey_number')
                    if team:
                        break

            # Create player display name
            if jersey_number:
                player_name = f"Player #{jersey_number}"
            else:
                player_name = f"Player ID {player_id}"

            stats_list.append({
                'player_id': player_id,
                'jersey_number': jersey_number,
                'player_name': player_name,
                'team': team if team else 'Unknown',
                'total_distance_m': round(total_distance[player_id], 2),
                'max_speed_kmh': round(max_speed[player_id], 2),
                'avg_speed_kmh': round(avg_speed[player_id], 2)
            })

        # Sort by total distance
        stats_list.sort(key=lambda x: x['total_distance_m'], reverse=True)

        # Export to JSON
        json_path = f"{self.output_dir}/{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(self._to_jsonable(stats_list), f, indent=2)

        # Export to CSV
        csv_path = f"{self.output_dir}/{filename}.csv"
        df = pd.DataFrame(stats_list)
        df.to_csv(csv_path, index=False)

        print(f"✅ Exported player stats to {json_path} and {csv_path}")

        return stats_list

    def export_team_stats(self, team_ball_control, passes, shots, filename='team_stats'):
        """
        Export team-level statistics
        """
        # Calculate possession
        team_1_frames = (team_ball_control == 1).sum()
        team_2_frames = (team_ball_control == 2).sum()
        total_frames = team_1_frames + team_2_frames

        if total_frames > 0:
            team_1_possession = (team_1_frames / total_frames) * 100
            team_2_possession = (team_2_frames / total_frames) * 100
        else:
            team_1_possession = 0
            team_2_possession = 0

        # Count passes by team
        team_1_passes = sum(1 for p in passes if p.get('team') == 1)
        team_2_passes = sum(1 for p in passes if p.get('team') == 2)

        # Count shots by team
        team_1_shots = sum(1 for s in shots if s.get('team') == 1)
        team_2_shots = sum(1 for s in shots if s.get('team') == 2)

        team_stats = {
            'team_1': {
                'possession_percent': round(team_1_possession, 2),
                'total_passes': team_1_passes,
                'total_shots': team_1_shots,
                'possession_frames': int(team_1_frames)
            },
            'team_2': {
                'possession_percent': round(team_2_possession, 2),
                'total_passes': team_2_passes,
                'total_shots': team_2_shots,
                'possession_frames': int(team_2_frames)
            }
        }

        # Export to JSON
        json_path = f"{self.output_dir}/{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(self._to_jsonable(team_stats), f, indent=2)

        print(f"✅ Exported team stats to {json_path}")

        return team_stats

    def export_events(self, passes, shots, interceptions, filename='events'):
        """
        Export all detected events
        """
        events = {
            'passes': passes,
            'shots': shots,
            'interceptions': interceptions,
            'summary': {
                'total_passes': len(passes),
                'total_shots': len(shots),
                'total_interceptions': len(interceptions)
            }
        }

        # Export to JSON
        json_path = f"{self.output_dir}/{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(self._to_jsonable(events), f, indent=2)

        # Export passes to CSV
        if passes:
            csv_path = f"{self.output_dir}/passes.csv"
            df = pd.DataFrame(passes)
            df.to_csv(csv_path, index=False)

        # Export shots to CSV
        if shots:
            csv_path = f"{self.output_dir}/shots.csv"
            df = pd.DataFrame(shots)
            df.to_csv(csv_path, index=False)

        print(f"✅ Exported events to {json_path}")

        return events

    def generate_html_report(self, player_stats, team_stats, events, video_name='Match Analysis'):
        """
        Generate comprehensive HTML report
        """
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Football Analysis Report - {video_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .stats-container {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .team-1 {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .team-2 {{
            color: #3498db;
            font-weight: bold;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>⚽ Football Analysis Report</h1>
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>📊 Team Statistics</h2>
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-value team-1">{team_stats['team_1']['possession_percent']}%</div>
            <div class="stat-label">Team 1 Possession</div>
        </div>
        <div class="stat-card">
            <div class="stat-value team-2">{team_stats['team_2']['possession_percent']}%</div>
            <div class="stat-label">Team 2 Possession</div>
        </div>
    </div>

    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-value team-1">{team_stats['team_1']['total_passes']}</div>
            <div class="stat-label">Team 1 Passes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value team-2">{team_stats['team_2']['total_passes']}</div>
            <div class="stat-label">Team 2 Passes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value team-1">{team_stats['team_1']['total_shots']}</div>
            <div class="stat-label">Team 1 Shots</div>
        </div>
        <div class="stat-card">
            <div class="stat-value team-2">{team_stats['team_2']['total_shots']}</div>
            <div class="stat-label">Team 2 Shots</div>
        </div>
    </div>

    <h2>👥 Player Performance</h2>
    <table>
        <tr>
            <th>Player ID</th>
            <th>Team</th>
            <th>Distance (m)</th>
            <th>Max Speed (km/h)</th>
            <th>Avg Speed (km/h)</th>
        </tr>
"""

        for player in player_stats[:15]:  # Top 15 players
            team_class = f"team-{player['team']}" if player['team'] != 'Unknown' else ''
            html_content += f"""
        <tr>
            <td>Player {player['player_id']}</td>
            <td class="{team_class}">Team {player['team']}</td>
            <td>{player['total_distance_m']}</td>
            <td>{player['max_speed_kmh']}</td>
            <td>{player['avg_speed_kmh']}</td>
        </tr>
"""

        html_content += f"""
    </table>

    <h2>🎯 Events Summary</h2>
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-value">{events['summary']['total_passes']}</div>
            <div class="stat-label">Total Passes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{events['summary']['total_shots']}</div>
            <div class="stat-label">Total Shots</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{events['summary']['total_interceptions']}</div>
            <div class="stat-label">Interceptions</div>
        </div>
    </div>

    <p style="text-align: center; color: #95a5a6; margin-top: 40px;">
        Generated with Tunisia Football AI Platform 🇹🇳
    </p>
</body>
</html>
"""

        # Save HTML report
        html_path = f"{self.output_dir}/analysis_report.html"
        with open(html_path, 'w') as f:
            f.write(html_content)

        print(f"✅ Generated HTML report: {html_path}")

        return html_path

    def export_all(self, tracks, total_distance, max_speed, avg_speed,
                   team_ball_control, passes, shots, interceptions):
        """
        Export all analytics data
        """
        print("\n📊 Exporting analytics data...")

        # Export player stats
        player_stats = self.export_player_stats(tracks, total_distance, max_speed, avg_speed)

        # Export team stats
        team_stats = self.export_team_stats(team_ball_control, passes, shots)

        # Export events
        events = self.export_events(passes, shots, interceptions)

        # Generate HTML report
        html_path = self.generate_html_report(player_stats, team_stats, events)

        print(f"\n✅ All analytics exported to: {self.output_dir}")

        return {
            'player_stats': player_stats,
            'team_stats': team_stats,
            'events': events,
            'html_report': html_path
        }
