#!/bin/bash

echo "Defense News Pipeline - Startup Script"
echo "======================================="

# Create necessary directories
echo "Creating data directory..."
mkdir -p data
mkdir -p credentials

# Debug: Show what variables are available
echo ""
echo "Checking Railway environment variables..."
python3 debug_env.py
echo ""

# Check if credentials file exists
if [ -f "credentials/google_service_account.json" ]; then
    echo "✓ Google credentials file found"
else
    echo "⚠ Google credentials file not found (will fail when accessing Sheets)"
fi

echo ""
echo "Starting pipeline..."
echo "======================================="
echo ""

# Run the pipeline - don't exit on error, let Python handle it
exec python3 pipeline.py
