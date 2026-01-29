"""
API configuration settings.
"""

import os
from dataclasses import dataclass


@dataclass
class APIConfig:
    """Configuration for the WhenWX API."""

    # Server settings
    host: str = os.getenv('API_HOST', '0.0.0.0')
    port: int = int(os.getenv('API_PORT', '8080'))
    debug: bool = os.getenv('API_DEBUG', 'false').lower() == 'true'

    # CORS settings
    cors_origins: list = None

    # GCS settings
    gcs_bucket: str = os.getenv('GCS_BUCKET', 'whenwx-data')
    gcs_prefix: str = os.getenv('GCS_PREFIX', 'output')

    # Rate limiting
    rate_limit: str = os.getenv('RATE_LIMIT', '1/minute')

    # Cache TTL (seconds)
    cache_ttl: int = int(os.getenv('CACHE_TTL', '300'))

    def __post_init__(self):
        if self.cors_origins is None:
            origins = os.getenv('CORS_ORIGINS', '*')
            self.cors_origins = origins.split(',') if origins != '*' else ['*']

    @property
    def zarr_path(self) -> str:
        """Full GCS path to zarr data."""
        return f'gs://{self.gcs_bucket}/{self.gcs_prefix}'


def get_config() -> APIConfig:
    """Get the API configuration."""
    return APIConfig()
