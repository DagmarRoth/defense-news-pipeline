#!/usr/bin/env python3
"""
Defense News Pipeline Orchestrator - Multi-Topic Edition

Continuously monitors DVIDS RSS feeds, analyzes content with Claude,
and routes items to user-defined topics with dedicated Google Sheets
and optional Slack notifications per topic.
"""

import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Note: load_dotenv() removed - Railway provides environment variables directly
# For local development, uncomment: from dotenv import load_dotenv; load_dotenv()

import scraper
import analyzer
import topic_manager
import keyword_matcher
from notifiers import (
    load_notification_state,
    save_notification_state,
    is_topic_slack_sent,
    mark_topic_slack_sent,
    is_topic_sheets_logged,
    mark_topic_sheets_logged,
    initialize_topic_state,
)
from notifiers.slack_notifier import send_slack_notification
from notifiers.sheets_logger import (
    init_sheets_client,
    get_or_create_topic_worksheet,
    append_item_to_sheet
)


# Configuration from environment variables
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL_SECONDS', 300))
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/google_service_account.json')


def validate_configuration():
    """Validate that all required configuration is set."""
    errors = []

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
    print("DEFENSE NEWS PIPELINE - MULTI-TOPIC MONITORING")
    print("="*70)
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print(f"Spreadsheet ID: {GOOGLE_SHEETS_SPREADSHEET_ID}")
    print("Press Ctrl+C to stop gracefully\n")

    # Validate configuration
    if not validate_configuration():
        sys.exit(1)

    # Initialize Google Sheets
    try:
        sheets_client = init_sheets_client(GOOGLE_CREDENTIALS_PATH)
        print(f"✓ Google Sheets client initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize Google Sheets: {e}")
        sys.exit(1)

    # Load initial state
    state = load_notification_state()
    print(f"✓ Loaded notification state\n")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"Iteration {iteration} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*70)

            try:
                # Skip work on first iteration (allows build validation to complete)
                # Start actual work on iteration 2
                if iteration == 1:
                    print("\n✓ Pipeline started successfully")
                    print("  (Skipping work on first iteration to allow build validation)")
                    print(f"  Will start monitoring topics in {POLL_INTERVAL} seconds...\n")
                    time.sleep(POLL_INTERVAL)
                    continue

                # Step 0: Check if topics are configured
                print("\n0️⃣  Loading active topics...")
                topics = topic_manager.list_active_topics()

                if not topics:
                    print("  ⚠ No active topics configured yet.")
                    print("  → Add topics via the web UI, then items will be monitored")
                    print(f"  → Next check in {POLL_INTERVAL} seconds...")
                    time.sleep(POLL_INTERVAL)
                    continue

                print(f"  ✓ Found {len(topics)} active topic(s)\n")

                # Step 1: Scrape for new items
                print("1️⃣  Scraping DVIDS for new items...")
                new_items = scraper.main()

                if not new_items:
                    print("  No new items found. Waiting for next poll...")
                    time.sleep(POLL_INTERVAL)
                    continue

                print(f"  ✓ Found {len(new_items)} new item(s)")

                # Step 2: Analyze new items
                print("\n2️⃣  Analyzing items with Claude...")
                analyzed_items = analyzer.analyze_all_items(new_items)

                # Step 3: Process each topic
                print("\n3️⃣  Processing topics...")
                total_slack_sent = 0
                total_sheets_logged = 0

                for topic in topics:
                    topic_id = topic['id']
                    topic_name = topic['name']

                    print(f"\n  📌 Topic: {topic_name}")

                    # Initialize state for this topic if needed
                    initialize_topic_state(topic_id, state)

                    # Filter items for this topic
                    matching_items = keyword_matcher.filter_items_by_topic(
                        analyzed_items,
                        topic
                    )

                    if not matching_items:
                        print(f"     → No matching items for this topic")
                        continue

                    print(f"     → Found {len(matching_items)} matching item(s)")

                    # Get or create worksheet for this topic
                    try:
                        worksheet = get_or_create_topic_worksheet(
                            sheets_client,
                            GOOGLE_SHEETS_SPREADSHEET_ID,
                            topic['sheet_name']
                        )
                    except Exception as e:
                        print(f"     ✗ Failed to access worksheet: {e}")
                        continue

                    # Process each matching item
                    for item in matching_items:
                        guid = item['guid']
                        score = item['analysis']['score']
                        title = item['title'][:50]

                        # Log to Google Sheets
                        if not is_topic_sheets_logged(topic_id, guid, state):
                            if append_item_to_sheet(worksheet, item):
                                mark_topic_sheets_logged(topic_id, guid, state)
                                total_sheets_logged += 1
                        else:
                            print(f"     ℹ Already logged: {title}...")

                        # Send to Slack if configured and score meets threshold
                        if topic.get('slack_webhook'):
                            if score >= topic.get('score_threshold', 5):
                                if not is_topic_slack_sent(topic_id, guid, state):
                                    if send_slack_notification(
                                        topic['slack_webhook'],
                                        item,
                                        topic_name=topic_name
                                    ):
                                        mark_topic_slack_sent(topic_id, guid, state)
                                        total_slack_sent += 1
                                else:
                                    print(f"     ℹ Already notified in Slack: {title}...")

                # Step 5: Save updated state
                save_notification_state(state)
                print(f"\n✓ Summary: Sent {total_slack_sent} Slack alert(s), "
                      f"logged {total_sheets_logged} item(s) across all topics")

            except KeyboardInterrupt:
                print("\n\n⏹ Shutdown signal received. Saving state and exiting gracefully...")
                save_notification_state(state)
                print("State saved. Goodbye!")
                break

            except Exception as e:
                print(f"\n✗ Error in pipeline iteration: {e}")
                import traceback
                traceback.print_exc()
                print(f"  Waiting 60 seconds before retry...")
                time.sleep(60)
                continue

            # Wait for next poll
            print(f"\n⏳ Waiting {POLL_INTERVAL} seconds until next poll...")
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n⏹ Shutdown signal received. Exiting...")
        save_notification_state(state)


if __name__ == '__main__':
    main()
