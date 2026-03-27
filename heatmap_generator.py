import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

class HeatmapGenerator:
    """
    Generate player heatmaps for tactical analysis
    """
    def __init__(self, pitch_width=1050, pitch_height=680):
        self.pitch_width = pitch_width
        self.pitch_height = pitch_height

    def generate_player_heatmap(self, tracks, player_id, homography=None):
        """
        Generate heatmap for a specific player
        """
        # Create blank heatmap
        heatmap = np.zeros((self.pitch_height, self.pitch_width), dtype=np.float32)

        # Collect all positions for this player
        positions = []

        for frame_tracks in tracks.get('players', []):
            if player_id in frame_tracks:
                position = frame_tracks[player_id].get('position')
                field_position = frame_tracks[player_id].get('field_position')

                if field_position is not None:
                    x, y = field_position
                    heatmap_x = int((x + 52.5) * 10)
                    heatmap_y = int((y + 34) * 10)
                    if 0 <= heatmap_x < self.pitch_width and 0 <= heatmap_y < self.pitch_height:
                        positions.append((heatmap_x, heatmap_y))
                elif position is not None:
                    # Transform to pitch coordinates if homography available
                    if homography is not None:
                        try:
                            pt = np.array([[position[0], position[1]]], dtype=np.float32)
                            pt = pt.reshape(-1, 1, 2)
                            transformed = cv2.perspectiveTransform(pt, homography)
                            x, y = transformed[0][0]

                            # Map to heatmap coordinates (with offset to center)
                            heatmap_x = int((x + 52.5) * 10)  # 52.5m is half pitch length
                            heatmap_y = int((y + 34) * 10)    # 34m is half pitch width

                            # Ensure within bounds
                            if 0 <= heatmap_x < self.pitch_width and 0 <= heatmap_y < self.pitch_height:
                                positions.append((heatmap_x, heatmap_y))
                        except:
                            continue
                    else:
                        # Fallback: use pixel positions (scaled)
                        scale_x = self.pitch_width / 1920  # Assume 1920 width video
                        scale_y = self.pitch_height / 1080
                        x = int(position[0] * scale_x)
                        y = int(position[1] * scale_y)
                        if 0 <= x < self.pitch_width and 0 <= y < self.pitch_height:
                            positions.append((x, y))

        # Add positions to heatmap with Gaussian weighting
        for x, y in positions:
            # Add a Gaussian blob around each position
            for dx in range(-20, 21):
                for dy in range(-20, 21):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.pitch_width and 0 <= ny < self.pitch_height:
                        distance = np.sqrt(dx**2 + dy**2)
                        weight = np.exp(-distance**2 / (2 * 10**2))  # Gaussian
                        heatmap[ny, nx] += weight

        # Apply Gaussian filter for smoothing
        heatmap = gaussian_filter(heatmap, sigma=5)

        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        return heatmap

    def generate_team_heatmap(self, tracks, team_id, homography=None):
        """
        Generate combined heatmap for entire team
        """
        heatmap = np.zeros((self.pitch_height, self.pitch_width), dtype=np.float32)

        # Find all players in this team
        team_players = set()
        for frame_tracks in tracks.get('players', []):
            for player_id, track_info in frame_tracks.items():
                if track_info.get('team') == team_id:
                    team_players.add(player_id)

        # Generate heatmap for each player and combine
        for player_id in team_players:
            player_heatmap = self.generate_player_heatmap(tracks, player_id, homography)
            heatmap += player_heatmap

        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        return heatmap

    def create_pitch_background(self):
        """Create a blank pitch for overlay"""
        pitch = np.ones((self.pitch_height, self.pitch_width, 3), dtype=np.uint8) * 34

        # Draw pitch markings in white
        cv2.rectangle(pitch, (0, 0), (self.pitch_width-1, self.pitch_height-1), (255, 255, 255), 2)
        cv2.line(pitch, (self.pitch_width//2, 0), (self.pitch_width//2, self.pitch_height), (255, 255, 255), 2)
        cv2.circle(pitch, (self.pitch_width//2, self.pitch_height//2), 92, (255, 255, 255), 2)

        # Penalty areas
        cv2.rectangle(pitch, (0, int(self.pitch_height/2 - 202)),
                     (165, int(self.pitch_height/2 + 202)), (255, 255, 255), 2)
        cv2.rectangle(pitch, (self.pitch_width-165, int(self.pitch_height/2 - 202)),
                     (self.pitch_width, int(self.pitch_height/2 + 202)), (255, 255, 255), 2)

        return pitch

    def visualize_heatmap(self, heatmap, title="Player Heatmap", save_path=None):
        """
        Visualize heatmap with pitch overlay
        """
        # Create pitch background
        pitch = self.create_pitch_background()

        # Convert heatmap to color using colormap
        heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)

        # Blend with pitch
        alpha = 0.6
        output = cv2.addWeighted(pitch, 1-alpha, heatmap_colored, alpha, 0)

        # Add title
        cv2.putText(output, title, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        if save_path:
            cv2.imwrite(save_path, output)

        return output

    def generate_all_heatmaps(self, tracks, homography=None, output_dir='outputs/heatmaps'):
        """
        Generate heatmaps for all players and teams
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        heatmaps = {}

        # Get all unique player IDs and their teams
        player_teams = {}
        for frame_tracks in tracks.get('players', []):
            for player_id, track_info in frame_tracks.items():
                team = track_info.get('team', 0)
                player_teams[player_id] = team

        # Generate individual player heatmaps
        for player_id in player_teams.keys():
            heatmap = self.generate_player_heatmap(tracks, player_id, homography)
            output_path = f"{output_dir}/player_{player_id}_heatmap.jpg"
            self.visualize_heatmap(heatmap, f"Player {player_id} Heatmap", output_path)
            heatmaps[f'player_{player_id}'] = heatmap

        # Generate team heatmaps
        teams = set(player_teams.values())
        for team_id in teams:
            if team_id > 0:  # Skip team 0 (unassigned)
                heatmap = self.generate_team_heatmap(tracks, team_id, homography)
                output_path = f"{output_dir}/team_{team_id}_heatmap.jpg"
                self.visualize_heatmap(heatmap, f"Team {team_id} Heatmap", output_path)
                heatmaps[f'team_{team_id}'] = heatmap

        print(f"✅ Generated {len(heatmaps)} heatmaps in {output_dir}")

        return heatmaps
