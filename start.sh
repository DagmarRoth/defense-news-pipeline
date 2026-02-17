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

# Debug: Show what variables are available
echo ""
echo "Checking Railway environment variables..."
python3 debug_env.py
echo ""

echo ""
echo "Starting pipeline..."
echo "======================================="
echo ""

# Run the pipeline - don't exit on error, let Python handle it
exec python3 pipeline.py
