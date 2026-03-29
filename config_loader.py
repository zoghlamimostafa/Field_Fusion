"""
Configuration Loader
Centralized configuration management for Tunisia Football AI system
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for the Football AI system"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader

        Args:
            config_path: Path to config.yaml file. If None, uses default location
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✓ Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"Warning: Config file not found at {self.config_path}")
            print("Using default configuration")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            print("Using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file not found"""
        return {
            "video": {"frame_rate": 24},
            "models": {"yolo_model": "models/best.pt"},
            "ball_assignment": {"max_player_ball_distance": 70},
            "speed_distance": {"frame_window": 5, "frame_rate": 24},
            "pitch": {"length": 105, "width": 68},
            "camera": {"minimum_distance": 5},
            "export": {
                "output_dir": "outputs/",
                "reports_dir": "outputs/reports/",
                "heatmaps_dir": "outputs/heatmaps/"
            }
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., "video.frame_rate")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config = Config()
            frame_rate = config.get("video.frame_rate", 24)
            yolo_model = config.get("models.yolo_model")
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., "video.frame_rate")
            value: Value to set

        Example:
            config = Config()
            config.set("video.frame_rate", 30)
        """
        keys = key_path.split('.')
        config_ref = self.config

        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]

        config_ref[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to file

        Args:
            path: Path to save config. If None, uses original path
        """
        save_path = Path(path) if path else self.config_path

        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Configuration saved to {save_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def get_video_config(self) -> Dict[str, Any]:
        """Get video processing configuration"""
        return self.config.get('video', {})

    def get_model_paths(self) -> Dict[str, str]:
        """Get model file paths"""
        return self.config.get('models', {})

    def get_pitch_dimensions(self) -> tuple:
        """Get pitch dimensions (length, width) in meters"""
        pitch = self.config.get('pitch', {})
        return (pitch.get('length', 105), pitch.get('width', 68))

    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration"""
        return self.config.get('export', {})

    def is_phase2_enabled(self) -> bool:
        """Check if Phase 2 features are enabled"""
        return self.get('phase2.metabolic_power.enabled', False)

    def is_phase3_enabled(self) -> bool:
        """Check if Phase 3 (TacticAI) is enabled"""
        return self.get('phase3.tacticai.enabled', False)

    def __repr__(self) -> str:
        return f"Config(path='{self.config_path}')"


# Global configuration instance
_global_config = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance (singleton pattern)

    Args:
        config_path: Optional path to config file

    Returns:
        Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config(config_path)
    return _global_config


if __name__ == "__main__":
    # Test configuration loading
    print("Testing Configuration Loader")
    print("=" * 60)

    config = Config()

    print("\nVideo Configuration:")
    print(f"  Frame Rate: {config.get('video.frame_rate')}")
    print(f"  Input Path: {config.get('video.default_input_path')}")

    print("\nModel Paths:")
    print(f"  YOLO Model: {config.get('models.yolo_model')}")

    print("\nPitch Dimensions:")
    length, width = config.get_pitch_dimensions()
    print(f"  Length: {length}m, Width: {width}m")

    print("\nBall Assignment:")
    print(f"  Max Distance: {config.get('ball_assignment.max_player_ball_distance')}px")

    print("\nExport Configuration:")
    export_config = config.get_export_config()
    print(f"  Output Dir: {export_config.get('output_dir')}")
    print(f"  Formats: {export_config.get('formats')}")

    print("\n" + "=" * 60)
    print("✓ Configuration test completed")
