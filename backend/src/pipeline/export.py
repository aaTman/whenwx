"""
Export processed data to GCS as zarr.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging

import xarray as xr

logger = logging.getLogger(__name__)


class GCSExporter:
    """
    Exports processed weather data to Google Cloud Storage as zarr.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = 'output',
        project: Optional[str] = None
    ):
        """
        Initialize the GCS exporter.

        Args:
            bucket: GCS bucket name
            prefix: Path prefix within the bucket
            project: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        """
        self.bucket = bucket
        self.prefix = prefix
        self.project = project or os.getenv('GOOGLE_CLOUD_PROJECT')
        self._fs = None

    def _get_filesystem(self):
        """Lazily initialize the GCS filesystem."""
        if self._fs is None:
            import gcsfs
            self._fs = gcsfs.GCSFileSystem(
                project=self.project,
                token='google_default'
            )
        return self._fs

    def _get_mapper(self, path: str):
        """Get a zarr-compatible mapper for a GCS path."""
        fs = self._get_filesystem()
        return fs.get_mapper(path)

    @property
    def output_path(self) -> str:
        """Full GCS path for output."""
        return f'gs://{self.bucket}/{self.prefix}'

    def export(
        self,
        ds: xr.Dataset,
        chunk_spec: Dict[str, int],
        mode: str = 'w',
        compute: bool = True
    ) -> str:
        """
        Export a dataset to GCS as zarr.

        Args:
            ds: Dataset to export
            chunk_spec: Chunking specification for zarr
            mode: Write mode ('w' for overwrite, 'a' for append)
            compute: Whether to compute immediately (vs return delayed)

        Returns:
            GCS path where data was written
        """
        logger.info(f"Exporting dataset to {self.output_path}")

        # Rechunk for optimal access pattern
        ds_chunked = ds.chunk(chunk_spec)

        # Add processing metadata
        ds_chunked.attrs['processing_time'] = datetime.utcnow().isoformat()
        ds_chunked.attrs['output_path'] = self.output_path

        # Get mapper
        mapper = self._get_mapper(self.output_path)

        # Write to zarr
        if compute:
            ds_chunked.to_zarr(mapper, mode=mode, consolidated=True)
            logger.info(f"Successfully exported to {self.output_path}")
        else:
            return ds_chunked.to_zarr(mapper, mode=mode, consolidated=True, compute=False)

        return self.output_path


def export_to_local(
    ds: xr.Dataset,
    path: str,
    chunk_spec: Dict[str, int]
) -> str:
    """
    Export a dataset to local filesystem as zarr.

    Useful for testing without GCS access.

    Args:
        ds: Dataset to export
        path: Local path for output
        chunk_spec: Chunking specification

    Returns:
        Path where data was written
    """
    logger.info(f"Exporting dataset to {path}")

    ds_chunked = ds.chunk(chunk_spec)
    ds_chunked.attrs['processing_time'] = datetime.utcnow().isoformat()

    ds_chunked.to_zarr(path, mode='w', consolidated=True)

    logger.info(f"Successfully exported to {path}")
    return path
