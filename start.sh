#!/bin/bash
set -e

echo "Defense News Pipeline - Startup Script"
echo "======================================="

# Create necessary directories
echo "Creating data directory..."
mkdir -p data
mkdir -p credentials

# Check for required environment variables
echo "Checking environment variables..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    exit 1
fi

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "ERROR: SLACK_WEBHOOK_URL not set"
    exit 1
fi

if [ -z "$GOOGLE_SHEETS_SPREADSHEET_ID" ]; then
    echo "ERROR: GOOGLE_SHEETS_SPREADSHEET_ID not set"
    exit 1
fi

# Check for credentials file (will be mounted by Railway)
if [ ! -f "credentials/google_service_account.json" ]; then
    echo "WARNING: credentials/google_service_account.json not found"
    echo "This file must be uploaded to Railway as a volume"
fi

echo "Environment check passed!"
echo "Starting pipeline..."
echo ""

# Run the pipeline
exec python3 pipeline.py
