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

# Start pipeline as a completely detached daemon
# This allows the script to exit immediately while pipeline continues running
nohup python3 pipeline.py >> pipeline.log 2>&1 &

# Give it a moment to start
sleep 2

# Verify it started
if pgrep -f "python3 pipeline.py" > /dev/null; then
    echo "✓ Pipeline started successfully"
    echo "✓ Logs: pipeline.log"
    echo ""
    echo "Build complete. Pipeline is running in the background."

    # Exit immediately to allow build to complete
    exit 0
else
    echo "✗ Failed to start pipeline"
    echo "Check environment variables and credentials"
    exit 1
fi
