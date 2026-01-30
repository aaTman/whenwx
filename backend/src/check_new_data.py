"""
Check if new data is available on Arraylake.

This script compares the latest Arraylake commit timestamp against
the last processed timestamp stored in GCS. Exits with code 0 if
new data is available, 1 otherwise.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_last_processed_time() -> datetime | None:
    """Read the last processed timestamp from GCS."""
    try:
        from google.cloud import storage

        bucket_name = os.getenv('GCS_BUCKET', 'whenwx-forecast-data')
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob('last_processed.json')

        if not blob.exists():
            logger.info("No last_processed.json found - first run")
            return None

        content = blob.download_as_text()
        data = json.loads(content)
        timestamp = datetime.fromisoformat(data['timestamp'])
        logger.info(f"Last processed: {timestamp.isoformat()}")
        return timestamp
    except Exception as e:
        logger.warning(f"Could not read last processed time: {e}")
        return None


def get_arraylake_commit_time() -> datetime:
    """Get the latest commit timestamp from Arraylake."""
    from .pipeline.ingest import ArraylakeDataFetcher
    from .config import get_config

    config = get_config()
    fetcher = ArraylakeDataFetcher(
        org=config.arraylake_org,
        repo=config.arraylake_repo,
        token=config.arraylake_token
    )

    commit_time = fetcher.get_latest_commit_time()
    logger.info(f"Latest Arraylake commit: {commit_time.isoformat()}")
    return commit_time


def save_processed_time(timestamp: datetime):
    """Save the processed timestamp to GCS."""
    try:
        from google.cloud import storage

        bucket_name = os.getenv('GCS_BUCKET', 'whenwx-forecast-data')
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob('last_processed.json')

        data = {'timestamp': timestamp.isoformat()}
        blob.upload_from_string(json.dumps(data), content_type='application/json')
        logger.info(f"Saved processed time: {timestamp.isoformat()}")
    except Exception as e:
        logger.error(f"Could not save processed time: {e}")


def main():
    """Check for new data and exit with appropriate code."""
    # Get timestamps
    last_processed = get_last_processed_time()

    try:
        arraylake_time = get_arraylake_commit_time()
    except Exception as e:
        logger.error(f"Failed to get Arraylake commit time: {e}")
        # On error, proceed with processing to be safe
        print("NEW_DATA=true")
        sys.exit(0)

    # Compare
    if last_processed is None:
        logger.info("No previous processing - new data available")
        print("NEW_DATA=true")
        print(f"COMMIT_TIME={arraylake_time.isoformat()}")
        sys.exit(0)

    # Make both timezone-aware for comparison
    if last_processed.tzinfo is None:
        last_processed = last_processed.replace(tzinfo=timezone.utc)
    if arraylake_time.tzinfo is None:
        arraylake_time = arraylake_time.replace(tzinfo=timezone.utc)

    if arraylake_time > last_processed:
        logger.info("New data available!")
        print("NEW_DATA=true")
        print(f"COMMIT_TIME={arraylake_time.isoformat()}")
        sys.exit(0)
    else:
        logger.info("No new data - skipping processing")
        print("NEW_DATA=false")
        sys.exit(0)


if __name__ == '__main__':
    main()
