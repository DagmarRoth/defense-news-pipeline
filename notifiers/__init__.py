"""Notifier module for managing output integrations and state tracking."""

import json
import os
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("data") / ".notification_state.json"


def load_notification_state():
    """Load notification state from file, or create new if doesn't exist."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)

    return {
        "slack_sent": [],
        "sheets_logged": [],
        "last_updated": datetime.now().isoformat()
    }


def save_notification_state(state):
    """Save notification state to file."""
    state["last_updated"] = datetime.now().isoformat()

    # Create data directory if needed
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_slack_sent(guid, state):
    """Check if a GUID has already been sent to Slack."""
    return guid in state.get("slack_sent", [])


def mark_slack_sent(guid, state):
    """Mark a GUID as sent to Slack."""
    if "slack_sent" not in state:
        state["slack_sent"] = []

    if guid not in state["slack_sent"]:
        state["slack_sent"].append(guid)


def is_sheets_logged(guid, state):
    """Check if a GUID has already been logged to Google Sheets."""
    return guid in state.get("sheets_logged", [])


def mark_sheets_logged(guid, state):
    """Mark a GUID as logged to Google Sheets."""
    if "sheets_logged" not in state:
        state["sheets_logged"] = []

    if guid not in state["sheets_logged"]:
        state["sheets_logged"].append(guid)
