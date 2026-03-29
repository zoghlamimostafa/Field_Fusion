"""
Kloppy Data Loader for Tunisia Football AI
Provides unified interface to load data from multiple providers:
- StatsBomb (event data)
- SkillCorner (tracking data)
- Metrica Sports (tracking data)
- And 12+ other providers
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
try:
    from kloppy import statsbomb, wyscout, opta, tracab, skillcorner, metrica
    from kloppy.domain import Dataset, TrackingDataset, EventDataset
except ImportError as e:
    print(f"Warning: Some kloppy modules not available: {e}")
    # Provide fallback imports
    import kloppy
    statsbomb = getattr(kloppy, 'statsbomb', None)
    skillcorner = getattr(kloppy, 'skillcorner', None)
    metrica = getattr(kloppy, 'metrica', None)


@dataclass
class LoadedData:
    """Container for loaded football data"""
    dataset: Dataset
    provider: str
    data_type: str  # 'tracking' or 'event'

    # Convenience accessors
    @property
    def is_tracking(self) -> bool:
        return self.data_type == 'tracking'

    @property
    def is_event(self) -> bool:
        return self.data_type == 'event'


class KloppyDataLoader:
    """
    Unified data loader for multiple football data providers.
    Converts data to standardized format compatible with Tunisia Football AI pipeline.
    """

    def __init__(self):
        self.supported_providers = [
            'statsbomb', 'wyscout', 'opta', 'tracab', 'skillcorner',
            'metrica', 'epts', 'secondspectrum', 'datafactory'
        ]

    def load_statsbomb_open_data(
        self,
        match_id: int = 3788741  # Default: Barcelona vs Deportivo
    ) -> LoadedData:
        """
        Load StatsBomb open data (event data)

        Args:
            match_id: Match ID from StatsBomb open data

        Returns:
            LoadedData object with event dataset

        Example:
            >>> loader = KloppyDataLoader()
            >>> data = loader.load_statsbomb_open_data(match_id=3788741)
            >>> events = data.dataset.events
            >>> print(f"Loaded {len(events)} events")
        """
        dataset = statsbomb.load_open_data(match_id=match_id)

        return LoadedData(
            dataset=dataset,
            provider='statsbomb',
            data_type='event'
        )

    def load_statsbomb_from_files(
        self,
        event_data_path: str,
        lineup_data_path: str
    ) -> LoadedData:
        """
        Load StatsBomb data from local JSON files

        Args:
            event_data_path: Path to events JSON file
            lineup_data_path: Path to lineup JSON file

        Returns:
            LoadedData object with event dataset
        """
        dataset = statsbomb.load(
            event_data=event_data_path,
            lineup_data=lineup_data_path,
            event_types=['pass', 'shot', 'take_on', 'carry']
        )

        return LoadedData(
            dataset=dataset,
            provider='statsbomb',
            data_type='event'
        )

    def load_skillcorner_tracking(
        self,
        match_data_path: str,
        structured_data_path: str
    ) -> LoadedData:
        """
        Load SkillCorner tracking data (10 fps)

        Args:
            match_data_path: Path to SkillCorner match JSONL file
            structured_data_path: Path to structured data JSONL file

        Returns:
            LoadedData object with tracking dataset

        Example:
            >>> data = loader.load_skillcorner_tracking(
            ...     "skillcorner_match.jsonl",
            ...     "skillcorner_structured.jsonl"
            ... )
            >>> frames = data.dataset.frames
        """
        dataset = skillcorner.load(
            match_data=match_data_path,
            structured_data=structured_data_path,
            coordinates='skillcorner'
        )

        return LoadedData(
            dataset=dataset,
            provider='skillcorner',
            data_type='tracking'
        )

    def load_metrica_tracking(
        self,
        home_data_path: str,
        away_data_path: str,
        metadata_path: Optional[str] = None
    ) -> LoadedData:
        """
        Load Metrica Sports tracking data (CSV format)

        Args:
            home_data_path: Path to home team tracking CSV
            away_data_path: Path to away team tracking CSV
            metadata_path: Optional metadata file path

        Returns:
            LoadedData object with tracking dataset
        """
        dataset = metrica.load(
            home_data=home_data_path,
            away_data=away_data_path,
            metadata=metadata_path,
            coordinates='metrica'
        )

        return LoadedData(
            dataset=dataset,
            provider='metrica',
            data_type='tracking'
        )

    def load_epts_tracking(
        self,
        metadata_path: str,
        raw_data_path: str
    ) -> LoadedData:
        """
        Load FIFA EPTS format tracking data

        Args:
            metadata_path: Path to EPTS metadata XML file
            raw_data_path: Path to EPTS raw data file

        Returns:
            LoadedData object with tracking dataset

        Note: EPTS support depends on kloppy version
        """
        try:
            from kloppy import epts
            dataset = epts.load(
                metadata=metadata_path,
                raw_data=raw_data_path
            )

            return LoadedData(
                dataset=dataset,
                provider='epts',
                data_type='tracking'
            )
        except ImportError:
            raise NotImplementedError("EPTS support not available in this kloppy version")

    def convert_tracking_to_pipeline_format(
        self,
        loaded_data: LoadedData,
        frame_indices: Optional[List[int]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Convert kloppy tracking data to Tunisia Football AI pipeline format

        Args:
            loaded_data: LoadedData object from any tracking provider
            frame_indices: Optional list of frame indices to convert (default: all)

        Returns:
            Dictionary with 'players' and 'ball' tracking data in pipeline format

        Format:
            {
                'players': [
                    {
                        'frame': 0,
                        'player_id': 1,
                        'team': 1,
                        'bbox': [x1, y1, x2, y2],  # Pixel coordinates
                        'position': [x, y]  # Meter coordinates
                    },
                    ...
                ],
                'ball': [
                    {
                        'frame': 0,
                        'bbox': [x1, y1, x2, y2],
                        'position': [x, y]
                    },
                    ...
                ]
            }
        """
        if not loaded_data.is_tracking:
            raise ValueError("Can only convert tracking data")

        dataset = loaded_data.dataset
        frames = dataset.frames if frame_indices is None else [dataset.frames[i] for i in frame_indices]

        players_data = []
        ball_data = []

        for frame_idx, frame in enumerate(frames):
            # Convert player positions
            for player_data in frame.players_data:
                if player_data.coordinates is None:
                    continue

                # Get coordinates in meters
                x_m = player_data.coordinates.x
                y_m = player_data.coordinates.y

                # Convert to pixel coordinates (assuming 1080p, 105m x 68m pitch)
                # This is a simplified conversion - in production, use actual calibration
                x_px = (x_m / 105.0) * 1920
                y_px = (y_m / 68.0) * 1080

                # Create bounding box (approximate 2m x 2m player)
                bbox_width = (2.0 / 105.0) * 1920
                bbox_height = (2.0 / 68.0) * 1080

                players_data.append({
                    'frame': frame_idx,
                    'player_id': player_data.player.player_id,
                    'team': 1 if player_data.player.team == dataset.metadata.teams[0] else 2,
                    'bbox': [
                        x_px - bbox_width / 2,
                        y_px - bbox_height / 2,
                        x_px + bbox_width / 2,
                        y_px + bbox_height / 2
                    ],
                    'position': [x_m, y_m]
                })

            # Convert ball position
            if frame.ball_coordinates is not None:
                x_m = frame.ball_coordinates.x
                y_m = frame.ball_coordinates.y

                x_px = (x_m / 105.0) * 1920
                y_px = (y_m / 68.0) * 1080

                bbox_size = (0.22 / 105.0) * 1920  # Ball diameter ~22cm

                ball_data.append({
                    'frame': frame_idx,
                    'bbox': [
                        x_px - bbox_size / 2,
                        y_px - bbox_size / 2,
                        x_px + bbox_size / 2,
                        y_px + bbox_size / 2
                    ],
                    'position': [x_m, y_m]
                })

        return {
            'players': players_data,
            'ball': ball_data
        }

    def convert_events_to_training_data(
        self,
        loaded_data: LoadedData,
        event_types: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Convert kloppy event data to training data format for ML models

        Args:
            loaded_data: LoadedData object from any event provider
            event_types: Filter by event types (e.g., ['PASS', 'SHOT'])

        Returns:
            Dictionary with events organized by type

        Format:
            {
                'passes': [
                    {
                        'x_start': 30.0, 'y_start': 34.0,
                        'x_end': 50.0, 'y_end': 40.0,
                        'successful': True,
                        'player_id': 'P123',
                        'team': 1,
                        'timestamp': 15.3
                    },
                    ...
                ],
                'shots': [...],
                'all_events': [...]
            }
        """
        if not loaded_data.is_event:
            raise ValueError("Can only convert event data")

        dataset = loaded_data.dataset
        events = dataset.events

        # Filter by event type if specified
        if event_types:
            from kloppy.domain import EventType
            type_mapping = {
                'PASS': EventType.PASS,
                'SHOT': EventType.SHOT,
                'TAKE_ON': EventType.TAKE_ON,
                'CARRY': EventType.CARRY
            }
            event_type_objs = [type_mapping[et] for et in event_types if et in type_mapping]
            events = [e for e in events if e.event_type in event_type_objs]

        # Organize events by type
        passes = []
        shots = []
        all_events = []

        for event in events:
            base_event = {
                'player_id': event.player.player_id if event.player else None,
                'team': 1 if event.team == dataset.metadata.teams[0] else 2,
                'timestamp': event.timestamp,
                'period': event.period.id
            }

            # Add coordinates if available
            if hasattr(event, 'coordinates') and event.coordinates:
                base_event['x_start'] = event.coordinates.x
                base_event['y_start'] = event.coordinates.y

            # Handle different event types
            from kloppy.domain import EventType, PassResult, ShotResult

            if event.event_type == EventType.PASS:
                pass_event = base_event.copy()
                if hasattr(event, 'receiver_coordinates') and event.receiver_coordinates:
                    pass_event['x_end'] = event.receiver_coordinates.x
                    pass_event['y_end'] = event.receiver_coordinates.y
                if hasattr(event, 'result'):
                    pass_event['successful'] = event.result == PassResult.COMPLETE
                passes.append(pass_event)

            elif event.event_type == EventType.SHOT:
                shot_event = base_event.copy()
                if hasattr(event, 'result'):
                    shot_event['is_goal'] = event.result == ShotResult.GOAL
                if hasattr(event, 'result_coordinates') and event.result_coordinates:
                    shot_event['x_end'] = event.result_coordinates.x
                    shot_event['y_end'] = event.result_coordinates.y
                shots.append(shot_event)

            all_events.append(base_event)

        return {
            'passes': passes,
            'shots': shots,
            'all_events': all_events
        }

    def get_dataset_info(self, loaded_data: LoadedData) -> Dict[str, Any]:
        """
        Extract metadata and statistics from loaded dataset

        Args:
            loaded_data: Any LoadedData object

        Returns:
            Dictionary with dataset information
        """
        dataset = loaded_data.dataset
        metadata = dataset.metadata

        info = {
            'provider': loaded_data.provider,
            'data_type': loaded_data.data_type,
            'teams': [team.name for team in metadata.teams],
            'players': {
                team.name: [
                    {'id': p.player_id, 'name': p.name, 'jersey_no': p.jersey_no}
                    for p in team.players
                ]
                for team in metadata.teams
            },
            'pitch_dimensions': {
                'length': metadata.pitch_dimensions.x_dim.max,
                'width': metadata.pitch_dimensions.y_dim.max,
                'unit': 'meters'
            }
        }

        # Add data-specific stats
        if loaded_data.is_tracking:
            info['frame_count'] = len(dataset.frames)
            info['frame_rate'] = dataset.metadata.frame_rate
            info['duration_seconds'] = len(dataset.frames) / dataset.metadata.frame_rate

        elif loaded_data.is_event:
            info['event_count'] = len(dataset.events)
            info['event_types'] = list(set([str(e.event_type) for e in dataset.events]))

        return info


def demo_kloppy_loader():
    """
    Demonstrate kloppy data loader functionality
    """
    loader = KloppyDataLoader()

    print("=" * 80)
    print("Kloppy Data Loader Demo")
    print("=" * 80)

    print("\n1. Loading StatsBomb Open Data...")
    try:
        data = loader.load_statsbomb_open_data(match_id=3788741)
        info = loader.get_dataset_info(data)

        print(f"✓ Loaded {info['provider']} data ({info['data_type']})")
        print(f"  Teams: {info['teams'][0]} vs {info['teams'][1]}")
        print(f"  Events: {info['event_count']}")
        print(f"  Event types: {', '.join(info['event_types'][:5])}")

        # Convert to training data
        training_data = loader.convert_events_to_training_data(data, event_types=['PASS', 'SHOT'])
        print(f"  Passes: {len(training_data['passes'])}")
        print(f"  Shots: {len(training_data['shots'])}")

        print("\n✅ StatsBomb data loaded and converted successfully!")

    except Exception as e:
        print(f"⚠️ Could not load StatsBomb data: {e}")
        print("   (This is normal if you don't have internet connection)")

    print("\n" + "=" * 80)
    print("Demo complete! Kloppy loader is ready to use.")
    print("\nSupported providers:")
    for provider in loader.supported_providers:
        print(f"  - {provider}")
    print("=" * 80)


if __name__ == "__main__":
    demo_kloppy_loader()
