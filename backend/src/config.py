"""
Configuration settings for the WhenWX backend.
"""

import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class WeatherEventConfig:
    """Configuration for a weather event threshold."""

    event_id: str
    variable: str  # ECMWF variable name
    threshold: float  # Threshold value in native units
    operator: Literal['lt', 'gt', 'lte', 'gte', 'eq']
    unit: str
    description: str


# Weather events to process
WEATHER_EVENTS = [
    WeatherEventConfig(
        event_id='freezing',
        variable='t2m',
        threshold=263.15,  # -10°C in Kelvin
        operator='lt',
        unit='K',
        description='Temperature below -10°C',
    ),
    # Add more events here as needed
]


@dataclass
class Config:
    """Application configuration."""

    # Arraylake settings
    arraylake_org: str = os.getenv('ARRAYLAKE_ORG', 'earthmover-public')
    arraylake_repo: str = os.getenv('ARRAYLAKE_REPO', 'ecmwf-ifs-oper')
    arraylake_token: str = os.getenv('ARRAYLAKE_TOKEN', '')

    # GCS settings
    gcs_bucket: str = os.getenv('GCS_BUCKET', 'whenwx-data')
    gcs_output_prefix: str = os.getenv('GCS_OUTPUT_PREFIX', 'output')

    # Processing settings
    chunk_spec: dict = None

    def __post_init__(self):
        # Chunking optimized for point queries
        # Each point's full time series is in a single chunk
        self.chunk_spec = {
            'valid_time': -1,  # All timesteps together
            'latitude': 1,
            'longitude': 1,
        }

    @property
    def output_path(self) -> str:
        """Full GCS path for output data."""
        return f'gs://{self.gcs_bucket}/{self.gcs_output_prefix}'


def get_config() -> Config:
    """Get the application configuration."""
    return Config()
