#!/usr/bin/env python3
"""
Defense News Pipeline Orchestrator

Continuously monitors DVIDS RSS feeds, analyzes content with Claude,
and outputs to Slack (high-priority alerts) and Google Sheets (historical log).
"""

import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Note: load_dotenv() removed - Railway provides environment variables directly
# For local development, use: from dotenv import load_dotenv; load_dotenv()

import scraper
import analyzer
from notifiers import (
    load_notification_state,
    save_notification_state,
    is_slack_sent,
    mark_slack_sent,
    is_sheets_logged,
    mark_sheets_logged,
)
from notifiers.slack_notifier import send_slack_notification, is_notification_worthy
from notifiers.sheets_logger import init_sheets_client, get_or_create_sheet, append_item_to_sheet


# Configuration from environment variables
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL_SECONDS', 300))
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
SLACK_THRESHOLD = int(os.getenv('SLACK_SCORE_THRESHOLD', 6))
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/google_service_account.json')


def validate_configuration():
    """Validate that all required configuration is set."""
    errors = []

    if not SLACK_WEBHOOK_URL:
        errors.append("  ✗ SLACK_WEBHOOK_URL not set in environment variables")

    if not GOOGLE_SHEETS_SPREADSHEET_ID:
        errors.append("  ✗ GOOGLE_SHEETS_SPREADSHEET_ID not set in environment variables")

    if not Path(GOOGLE_CREDENTIALS_PATH).exists():
        errors.append(f"  ✗ Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}")
        errors.append("    (Upload to Railway Volumes → /app/credentials/)")

    if errors:
        print("\n" + "="*70)
        print("Configuration Validation Failed")
        print("="*70)
        for error in errors:
            print(error)
        print("\n→ For Railway: Check project Variables/Secrets")
        print("→ For local: Create .env file with required variables")
        return False

    return True


def main():
    """Main continuous monitoring loop."""
    print("\n" + "="*70)
    print("DEFENSE NEWS PIPELINE - CONTINUOUS MONITORING")
    print("="*70)
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print(f"Slack threshold: {SLACK_THRESHOLD}/10")
    print("Press Ctrl+C to stop gracefully\n")

    # Validate configuration
    if not validate_configuration():
        sys.exit(1)

    # Initialize Slack and Google Sheets
    try:
        sheets_client = init_sheets_client(GOOGLE_CREDENTIALS_PATH)
        worksheet = get_or_create_sheet(sheets_client, GOOGLE_SHEETS_SPREADSHEET_ID)
        print(f"✓ Google Sheets initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize Google Sheets: {e}")
        sys.exit(1)

    # Load initial state
    state = load_notification_state()
    print(f"Loaded state: {len(state.get('slack_sent', []))} items sent to Slack, "
          f"{len(state.get('sheets_logged', []))} items logged to Sheets\n")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"Iteration {iteration} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*70)

            try:
                # Step 1: Scrape for new items
                print("\n1. Scraping DVIDS for new items...")
                new_items = scraper.main()

                if not new_items:
                    print("  No new items found. Waiting for next poll...")
                    time.sleep(POLL_INTERVAL)
                    continue

                print(f"  Found {len(new_items)} new item(s)")

                # Step 2: Analyze new items
                print("\n2. Analyzing items with Claude...")
                analyzed_items = analyzer.analyze_all_items(new_items)

                # Step 3: Process each analyzed item
                print("\n3. Processing notifications and logging...")
                slack_sent = 0
                sheets_logged = 0

                for item in analyzed_items:
                    guid = item['guid']
                    score = item['analysis']['score']
                    title = item['title'][:50]

                    # Check if already processed
                    already_sent = is_slack_sent(guid, state)
                    already_logged = is_sheets_logged(guid, state)

                    if already_sent and already_logged:
                        print(f"  ⊘ Skip (already processed): {title}...")
                        continue

                    # Send to Slack if high-priority
                    if is_notification_worthy(item, SLACK_THRESHOLD):
                        if not already_sent:
                            if send_slack_notification(SLACK_WEBHOOK_URL, item):
                                mark_slack_sent(guid, state)
                                slack_sent += 1
                        else:
                            print(f"  ℹ Already sent to Slack: {title}...")
                    else:
                        print(f"  ○ Score {score}/10 (below {SLACK_THRESHOLD} threshold): {title}...")

                    # Log to Google Sheets
                    if not already_logged:
                        if append_item_to_sheet(worksheet, item):
                            mark_sheets_logged(guid, state)
                            sheets_logged += 1
                    else:
                        print(f"  ℹ Already logged to Sheets: {title}...")

                # Step 4: Save updated state
                save_notification_state(state)
                print(f"\n  Summary: Sent {slack_sent} Slack alert(s), logged {sheets_logged} item(s)")

            except KeyboardInterrupt:
                print("\n\nShutdown signal received. Saving state and exiting gracefully...")
                save_notification_state(state)
                print("State saved. Goodbye!")
                break

            except Exception as e:
                print(f"\n✗ Error in pipeline iteration: {e}")
                print(f"  Waiting 60 seconds before retry...")
                time.sleep(60)
                continue

            # Wait for next poll
            print(f"\nWaiting {POLL_INTERVAL} seconds until next poll...")
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nShutdown signal received. Exiting...")
        save_notification_state(state)


if __name__ == '__main__':
    main()
