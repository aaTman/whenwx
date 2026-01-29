"""
Data ingestion from Earthmover Arraylake.
"""

import os
from datetime import datetime
from typing import Optional
import logging

import xarray as xr

logger = logging.getLogger(__name__)


class ArraylakeDataFetcher:
    """
    Handles connection to Arraylake marketplace for ECMWF IFS data.
    """

    def __init__(
        self,
        org: str = 'extreme-earth',
        repo: str = 'ifs-hres',
        token: Optional[str] = None
    ):
        """
        Initialize the Arraylake data fetcher.

        Args:
            org: Arraylake organization name
            repo: Arraylake repository name
            token: API token (defaults to ARRAYLAKE_TOKEN env var)
        """
        self.org = org
        self.repo = repo
        self.token = token or os.getenv('ARRAYLAKE_TOKEN')
        self._client = None
        self._repo = None

    def _get_client(self):
        """Lazily initialize the Arraylake client."""
        if self._client is None:
            import arraylake
            self._client = arraylake.Client(token=self.token)
        return self._client

    def _get_repo(self):
        """Get the Arraylake repository."""
        if self._repo is None:
            client = self._get_client()
            self._repo = client.get_repo(f'{self.org}/{self.repo}')
        return self._repo

    def get_latest_forecast(self, branch: str = 'main') -> xr.Dataset:
        """
        Fetch the most recent forecast data.

        Args:
            branch: Repository branch to read from

        Returns:
            xarray Dataset with forecast data
        """
        logger.info(f"Fetching latest forecast from {self.org}/{self.repo}")

        repo = self._get_repo()
        session = repo.readonly_session(branch)

        ds = xr.open_zarr(
            session.store,
            decode_timedelta=True,
            consolidated=False
        )

        logger.info(f"Loaded dataset with variables: {list(ds.data_vars)}")
        return ds

    def get_latest_commit_time(self, branch: str = 'main') -> datetime:
        """
        Get the timestamp of the latest commit.

        Useful for detecting when new data is available.

        Args:
            branch: Repository branch to check

        Returns:
            Datetime of the latest commit
        """
        repo = self._get_repo()
        commits = repo.log(branch, limit=1)

        if not commits:
            raise ValueError(f"No commits found on branch {branch}")

        return commits[0].timestamp

    def detect_new_data(
        self,
        last_processed: datetime,
        branch: str = 'main'
    ) -> bool:
        """
        Check if new data is available since last processing.

        Args:
            last_processed: Timestamp of last processed data
            branch: Repository branch to check

        Returns:
            True if new data is available
        """
        try:
            latest_commit_time = self.get_latest_commit_time(branch)
            return latest_commit_time > last_processed
        except Exception as e:
            logger.warning(f"Failed to check for new data: {e}")
            return False


def create_mock_dataset() -> xr.Dataset:
    """
    Create a mock dataset for testing without Arraylake access.

    Returns:
        xarray Dataset mimicking ECMWF IFS structure
    """
    import numpy as np
    import pandas as pd

    # Create coordinates
    lats = np.arange(-90, 90.25, 0.25)
    lons = np.arange(-180, 180, 0.25)
    times = pd.date_range(start='2025-01-28', periods=121, freq='3h')

    # Create mock temperature data (with some locations below -10°C)
    np.random.seed(42)
    base_temp = 280  # ~7°C
    temp_data = base_temp + np.random.randn(len(times), len(lats), len(lons)) * 15

    # Add cold region in northern latitudes
    for i, lat in enumerate(lats):
        if lat > 60:
            temp_data[:, i, :] -= 30  # Make arctic cold

    ds = xr.Dataset(
        {
            '2t': (['time', 'latitude', 'longitude'], temp_data),
        },
        coords={
            'time': times,
            'latitude': lats,
            'longitude': lons,
        },
        attrs={
            'title': 'Mock ECMWF IFS Forecast',
            'source': 'Mock data for testing',
        }
    )

    return ds
