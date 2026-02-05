"""
Export processed data to zarr.
"""

import os
import shutil
from datetime import datetime
from typing import Dict, Optional
import logging

import numpy as np
import xarray as xr
import zarr

logger = logging.getLogger(__name__)


def _prepare_dataset_for_zarr(ds: xr.Dataset) -> xr.Dataset:
    """
    Prepare dataset for zarr export, handling NaT values properly.

    Converts timedelta64 arrays with NaT to float64 with NaN,
    since zarr doesn't handle timedelta64 NaT well (uses fill_value=0).
    """
    ds = ds.copy()

    for var_name in list(ds.data_vars):
        arr = ds[var_name]

        # Check if it's a timedelta type
        if np.issubdtype(arr.dtype, np.timedelta64):
            # Convert timedelta to hours as float, NaT becomes NaN
            values = arr.values
            # timedelta64 to float seconds, then to hours
            float_values = values.astype('timedelta64[s]').astype(float) / 3600.0
            # NaT in timedelta64 becomes a very large negative number when cast to float
            # Replace those with NaN
            float_values = np.where(
                np.isnat(values) | (float_values < -1e15),
                np.nan,
                float_values
            )
            # Use 'unit' (not 'units') to avoid xarray's timedelta auto-decoding
            # xarray looks for 'units' attribute to decode as timedelta
            new_attrs = {k: v for k, v in arr.attrs.items() if k != 'units'}
            new_attrs['unit'] = 'hours'  # singular 'unit' won't trigger decode
            ds[var_name] = xr.DataArray(
                float_values,
                dims=arr.dims,
                coords=arr.coords,
                attrs=new_attrs
            )
            logger.info(f"Converted {var_name} from timedelta64 to float64 hours")

    return ds


def export_to_local(
    ds: xr.Dataset,
    path: str,
    chunk_spec: Dict[str, int],
) -> str:
    """
    Export a dataset to local filesystem as zarr.

    Args:
        ds: Dataset to export
        path: Local path for output
        chunk_spec: Chunking specification

    Returns:
        Path where data was written
    """
    from dask.diagnostics import ProgressBar

    logger.info(f"Exporting dataset to {path}")
    logger.info(f"Dataset variables: {list(ds.data_vars)}")
    logger.info(f"Target chunk spec: {chunk_spec}")

    # Prepare dataset for zarr (handle NaT values)
    ds = _prepare_dataset_for_zarr(ds)

    # Clean up existing output
    if os.path.exists(path):
        shutil.rmtree(path)

    # Add metadata
    ds.attrs['processing_time'] = datetime.now().isoformat()

    # Apply chunking - resolve -1 to actual dimension sizes
    resolved_chunks = {}
    for dim, chunk_size in chunk_spec.items():
        if dim in ds.dims:
            if chunk_size == -1:
                resolved_chunks[dim] = ds.sizes[dim]
            else:
                resolved_chunks[dim] = min(chunk_size, ds.sizes[dim])

    logger.info(f"Resolved chunks: {resolved_chunks}")

    # Chunk the dataset
    ds_chunked = ds.chunk(resolved_chunks)

    # Log chunk info
    for var in ds_chunked.data_vars:
        arr = ds_chunked[var]
        logger.info(f"  {var}: shape={arr.shape}, chunks={arr.chunks}")

    # Write to zarr with progress
    logger.info("Writing to zarr...")
    with ProgressBar():
        ds_chunked.to_zarr(path, mode='w', consolidated=True)

    logger.info(f"Successfully exported to {path}")
    return path


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
        self.bucket = bucket
        self.prefix = prefix
        self.project = project or os.getenv('GOOGLE_CLOUD_PROJECT')
        self._fs = None

    def _get_filesystem(self):
        if self._fs is None:
            import gcsfs
            self._fs = gcsfs.GCSFileSystem(
                project=self.project,
                token='google_default'
            )
        return self._fs

    def _get_mapper(self, path: str):
        fs = self._get_filesystem()
        return fs.get_mapper(path)

    @property
    def output_path(self) -> str:
        return f'gs://{self.bucket}/{self.prefix}'

    def export(
        self,
        ds: xr.Dataset,
        chunk_spec: Dict[str, int],
    ) -> str:
        """Export dataset to GCS."""
        from dask.diagnostics import ProgressBar

        logger.info(f"Exporting dataset to {self.output_path}")

        # Prepare dataset for zarr (handle NaT values)
        ds = _prepare_dataset_for_zarr(ds)

        ds.attrs['processing_time'] = datetime.now().isoformat()
        ds.attrs['output_path'] = self.output_path

        # Resolve chunks
        resolved_chunks = {}
        for dim, chunk_size in chunk_spec.items():
            if dim in ds.dims:
                if chunk_size == -1:
                    resolved_chunks[dim] = ds.sizes[dim]
                else:
                    resolved_chunks[dim] = min(chunk_size, ds.sizes[dim])

        ds_chunked = ds.chunk(resolved_chunks)

        mapper = self._get_mapper(self.output_path)

        logger.info("Writing to GCS zarr...")
        with ProgressBar():
            ds_chunked.to_zarr(mapper, mode='w', consolidated=True)

        logger.info(f"Successfully exported to {self.output_path}")
        return self.output_path
