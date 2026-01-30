"""
Main entry point for the WhenWX backend processing pipeline.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import get_config, WEATHER_EVENTS
from .processors import TemperatureProcessor
from .pipeline.ingest import ArraylakeDataFetcher, create_mock_dataset
from .pipeline.export import GCSExporter, export_to_local

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_forecast(use_mock: bool = False, local_output: Optional[str] = None):
    """
    Process the latest forecast data and compute weather event metrics.

    Args:
        use_mock: If True, use mock data instead of Arraylake
        local_output: If provided, write to local path instead of GCS

    Returns:
        Path where processed data was written
    """
    config = get_config()

    logger.info("Starting forecast processing")

    # Fetch data
    if use_mock:
        logger.info("Using mock data")
        ds = create_mock_dataset()
    else:
        logger.info("Fetching from Arraylake")
        fetcher = ArraylakeDataFetcher(
            org=config.arraylake_org,
            repo=config.arraylake_repo,
            token=config.arraylake_token
        )
        ds = fetcher.get_latest_forecast()

    # Process each weather event
    results = {}

    for event_config in WEATHER_EVENTS:
        logger.info(f"Processing event: {event_config.event_id}")

        if event_config.variable == '2t':
            processor = TemperatureProcessor(
                event_id=event_config.event_id,
                threshold_kelvin=event_config.threshold,
                operator=event_config.operator,
                variable=event_config.variable
            )
        else:
            logger.warning(f"No processor for variable: {event_config.variable}")
            continue

        try:
            # Use 'step' dimension for ECMWF IFS data (forecast lead time)
            time_dim = 'step' if 'step' in ds.dims else 'time'
            metrics = processor.compute_metrics(ds, time_dim=time_dim)
            results[event_config.event_id] = metrics
            logger.info(f"Computed metrics for {event_config.event_id}")
        except Exception as e:
            logger.error(f"Failed to process {event_config.event_id}: {e}")
            continue

    if not results:
        logger.error("No events were processed successfully")
        return None

    # Merge all results into a single dataset
    # Prefix variable names with event_id for uniqueness
    merged_vars = {}
    for event_id, event_ds in results.items():
        for var_name in event_ds.data_vars:
            merged_vars[f'{event_id}_{var_name}'] = event_ds[var_name]

    output_ds = xr.Dataset(merged_vars)

    # Add global attributes
    output_ds.attrs = {
        'title': 'WhenWX Processed Weather Event Data',
        'source': 'ECMWF IFS 15-day forecast via Earthmover Arraylake',
        'institution': 'WhenWX',
        'processing_time': datetime.now(timezone.utc).isoformat(),
        'events_processed': list(results.keys()),
    }

    # Export
    if local_output:
        output_path = export_to_local(
            output_ds,
            local_output,
            config.chunk_spec
        )
    else:
        exporter = GCSExporter(
            bucket=config.gcs_bucket,
            prefix=config.gcs_output_prefix
        )
        output_path = exporter.export(
            output_ds,
            config.chunk_spec
        )

    logger.info(f"Processing complete. Output: {output_path}")
    return output_path


# Need this import at module level for the merged dataset
import xarray as xr


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process weather forecast data')
    parser.add_argument('--mock', action='store_true', help='Use mock data')
    parser.add_argument('--local', type=str, help='Local output path')

    args = parser.parse_args()

    process_forecast(use_mock=args.mock, local_output=args.local)
