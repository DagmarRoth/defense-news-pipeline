#!/bin/bash

echo "Defense News Pipeline - Startup Script"
echo "======================================="

# Create necessary directories
echo "Creating data directory..."
mkdir -p data
mkdir -p credentials

# Decode Google credentials from base64 environment variable if available
if [ -n "$GOOGLE_CREDENTIALS_BASE64" ]; then
    echo "Decoding Google credentials from environment variable..."
    echo "$GOOGLE_CREDENTIALS_BASE64" | base64 -d > credentials/google_service_account.json
    echo "✓ Google credentials file created"
elif [ -f "credentials/google_service_account.json" ]; then
    echo "✓ Google credentials file found"
else
    echo "⚠ Google credentials not available (set GOOGLE_CREDENTIALS_BASE64 or upload file)"
fi

# Verify we have minimum required environment variables before starting
echo ""
echo "Verifying environment variables..."
MISSING_VARS=""
for var in GOOGLE_SHEETS_SPREADSHEET_ID ANTHROPIC_API_KEY; do
    if [ -z "${!var}" ]; then
        MISSING_VARS="$MISSING_VARS $var"
    fi
done

if [ -n "$MISSING_VARS" ]; then
    echo "⚠ ERROR: Missing required environment variables:$MISSING_VARS"
    echo "Pipeline cannot start without these variables."
    echo "Please set them in Railway environment variables and redeploy."
    echo ""
    echo "Keeping container alive for debugging..."
    # Keep container running so we can check logs
    tail -f /dev/null
fi

echo "✓ All required environment variables are set"
echo ""

echo "Starting pipeline..."
echo "======================================="
echo ""

# Start pipeline in background so it continues after script exits
# Use setsid to create new process group so it survives shell exit
setsid bash -c 'timeout 1800 python3 pipeline.py > pipeline.log 2>&1' &
PIPELINE_PID=$!

if [ $? -eq 0 ]; then
    echo "✓ Pipeline started (PID: $PIPELINE_PID)"
    echo "✓ Logs: pipeline.log"
else
    echo "✗ Failed to start pipeline"
    exit 1
fi

echo ""
echo "Pipeline is running. Keeping container alive..."
echo ""

# Keep the container running indefinitely
# The background pipeline process will continue to run independently
while true; do
    sleep 60
    # Optionally check if pipeline is still running
    if ! kill -0 $PIPELINE_PID 2>/dev/null; then
        echo "⚠ Warning: Pipeline process exited. Restarting..."
        setsid bash -c 'timeout 1800 python3 pipeline.py > pipeline.log 2>&1' &
        PIPELINE_PID=$!
    fi
done
