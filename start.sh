#!/bin/bash

echo "Defense News Pipeline - Startup Script"
echo "======================================="

# Create necessary directories
echo "Creating data directory..."
mkdir -p data
mkdir -p credentials

# Debug: Show what variables are available
echo ""
echo "Environment variables status:"
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}... (${#ANTHROPIC_API_KEY} chars)"
echo "  SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL:0:50}..."
echo "  GOOGLE_SHEETS_SPREADSHEET_ID: ${GOOGLE_SHEETS_SPREADSHEET_ID:0:20}..."
echo "  SLACK_SCORE_THRESHOLD: ${SLACK_SCORE_THRESHOLD:-not set}"
echo "  POLL_INTERVAL_SECONDS: ${POLL_INTERVAL_SECONDS:-not set}"
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
