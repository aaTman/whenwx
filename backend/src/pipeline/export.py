"""
Export processed data to GCS as zarr using rechunker with Dask distributed.
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Optional
import logging

import xarray as xr
import zarr
from rechunker import rechunk

logger = logging.getLogger(__name__)


def get_dask_client(n_workers: int = 4, threads_per_worker: int = 2, memory_limit: str = "4GB"):
    """
    Get or create a Dask distributed client for parallel processing.

    Args:
        n_workers: Number of worker processes
        threads_per_worker: Threads per worker
        memory_limit: Memory limit per worker

    Returns:
        Dask distributed Client
    """
    from dask.distributed import Client, LocalCluster

    # Check if we already have a client
    try:
        from dask.distributed import get_client
        client = get_client()
        logger.info(f"Using existing Dask client: {client.dashboard_link}")
        return client
    except ValueError:
        pass

    # Create a new local cluster
    logger.info(f"Creating Dask LocalCluster with {n_workers} workers...")
    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        memory_limit=memory_limit,
    )
    client = Client(cluster)
    logger.info(f"Dask dashboard available at: {client.dashboard_link}")
    return client


def rechunk_with_dask(
    ds: xr.Dataset,
    target_chunks: Dict[str, int],
    target_path: str,
    temp_path: Optional[str] = None,
    max_mem: str = "2GB",
    n_workers: int = 4,
) -> str:
    """
    Rechunk a dataset using Dask distributed for parallel processing.

    Args:
        ds: Source dataset
        target_chunks: Target chunking specification
        target_path: Path for output zarr
        temp_path: Path for intermediate storage
        max_mem: Maximum memory per rechunker operation
        n_workers: Number of Dask workers

    Returns:
        Path to the rechunked zarr store
    """
    from dask.distributed import progress

    # Create temp directory if not provided
    cleanup_temp = False
    if temp_path is None:
        temp_path = tempfile.mkdtemp(prefix="rechunker_temp_")
        cleanup_temp = True

    source_path = tempfile.mkdtemp(prefix="rechunker_source_")

    try:
        # Start Dask client
        client = get_dask_client(n_workers=n_workers)

        # Write source dataset to zarr first (keeping original chunks)
        logger.info("Writing source dataset to temporary zarr...")
        ds.to_zarr(source_path, mode='w')
        logger.info(f"Source written to {source_path}")

        # Open as zarr group
        source_group = zarr.open(source_path, mode='r')

        # Build target chunks for each array
        target_chunks_full = {}
        for var in source_group.array_keys():
            arr = source_group[var]
            dims = arr.attrs.get('_ARRAY_DIMENSIONS', [])
            if dims:
                var_chunks = tuple(
                    target_chunks.get(dim, arr.shape[i]) if target_chunks.get(dim, -1) != -1
                    else arr.shape[i]
                    for i, dim in enumerate(dims)
                )
                target_chunks_full[var] = var_chunks
                logger.info(f"  {var}: {arr.shape} -> chunks {var_chunks}")

        logger.info(f"Target chunks: {target_chunks}")
        logger.info(f"Temp store: {temp_path}")

        # Create rechunk plan
        rechunk_plan = rechunk(
            source_group,
            target_chunks_full,
            max_mem,
            target_path,
            temp_store=temp_path,
        )

        # Execute with Dask - this returns a future
        logger.info("Executing rechunk plan with Dask distributed...")
        logger.info(f"Monitor progress at: {client.dashboard_link}")

        # Execute and wait
        result = rechunk_plan.execute()

        # If result is a dask object, compute it
        if hasattr(result, 'compute'):
            result.compute()

        logger.info(f"Rechunking complete! Output: {target_path}")
        return target_path

    finally:
        # Cleanup temp directories
        if os.path.exists(source_path):
            shutil.rmtree(source_path)
        if cleanup_temp and os.path.exists(temp_path):
            shutil.rmtree(temp_path)


def export_to_local_simple(
    ds: xr.Dataset,
    path: str,
    chunk_spec: Dict[str, int],
) -> str:
    """
    Simple export without rechunking - just writes with specified chunks.

    Use this for testing or when source chunks are already acceptable.
    """
    from dask.diagnostics import ProgressBar

    logger.info(f"Exporting dataset to {path} (simple mode)")

    if os.path.exists(path):
        shutil.rmtree(path)

    ds.attrs['processing_time'] = datetime.utcnow().isoformat()

    # Chunk and write
    ds_chunked = ds.chunk(chunk_spec)

    logger.info("Writing to zarr...")
    with ProgressBar():
        ds_chunked.to_zarr(path, mode='w', consolidated=True)

    logger.info(f"Successfully exported to {path}")
    return path


def export_to_local(
    ds: xr.Dataset,
    path: str,
    chunk_spec: Dict[str, int],
    max_mem: str = "2GB",
    n_workers: int = 4,
    use_dask: bool = True,
) -> str:
    """
    Export a dataset to local filesystem as zarr.

    Args:
        ds: Dataset to export
        path: Local path for output
        chunk_spec: Chunking specification
        max_mem: Maximum memory for rechunker
        n_workers: Number of Dask workers
        use_dask: Whether to use Dask distributed (recommended for large rechunks)

    Returns:
        Path where data was written
    """
    logger.info(f"Exporting dataset to {path}")
    ds.attrs['processing_time'] = datetime.utcnow().isoformat()

    if os.path.exists(path):
        shutil.rmtree(path)

    if use_dask:
        rechunk_with_dask(
            ds,
            chunk_spec,
            path,
            max_mem=max_mem,
            n_workers=n_workers,
        )
    else:
        export_to_local_simple(ds, path, chunk_spec)

    # Consolidate metadata
    zarr.consolidate_metadata(path)

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
        max_mem: str = "2GB",
        n_workers: int = 4,
    ) -> str:
        """Export dataset to GCS with rechunking."""
        logger.info(f"Exporting dataset to {self.output_path}")

        ds.attrs['processing_time'] = datetime.utcnow().isoformat()
        ds.attrs['output_path'] = self.output_path

        mapper = self._get_mapper(self.output_path)

        rechunk_with_dask(
            ds,
            chunk_spec,
            mapper,
            max_mem=max_mem,
            n_workers=n_workers,
        )

        zarr.consolidate_metadata(mapper)

        logger.info(f"Successfully exported to {self.output_path}")
        return self.output_path
