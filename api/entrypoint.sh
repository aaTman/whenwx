#!/bin/bash
set -e

# If GOOGLE_APPLICATION_CREDENTIALS_JSON is set, write it to a file
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS_JSON" ]; then
    echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > /tmp/gcp-credentials.json
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json
    echo "GCP credentials configured"
fi

# Start the application
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8080
