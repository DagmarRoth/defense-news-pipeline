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
            state = json.load(f)
            # Auto-migrate old format to new format
            return _migrate_state_format(state)

    return {
        "topics": {},
        "last_updated": datetime.now().isoformat()
    }


def _migrate_state_format(state):
    """
    Auto-migrate state from old global format to new per-topic format.

    Old format:
    {
        "slack_sent": ["guid1"],
        "sheets_logged": ["guid1"]
    }

    New format:
    {
        "topics": {
            "topic-uuid": {
                "slack_sent": ["guid1"],
                "sheets_logged": ["guid1"]
            }
        }
    }
    """
    # If already in new format, return as-is
    if "topics" in state:
        return state

    # If in old format, migrate to new format
    if "slack_sent" in state or "sheets_logged" in state:
        migrated = {
            "topics": {},
            "last_updated": state.get("last_updated", datetime.now().isoformat())
        }
        return migrated

    # Unknown format, return new format
    return {
        "topics": {},
        "last_updated": state.get("last_updated", datetime.now().isoformat())
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


# ============================================================================
# NEW: Per-Topic State Tracking Functions
# ============================================================================

def _get_or_create_topic_state(topic_id, state):
    """Get or create state dict for a topic."""
    if "topics" not in state:
        state["topics"] = {}

    if topic_id not in state["topics"]:
        state["topics"][topic_id] = {
            "slack_sent": [],
            "sheets_logged": []
        }

    return state["topics"][topic_id]


def is_topic_slack_sent(topic_id, guid, state):
    """Check if a GUID has been sent to Slack for a specific topic."""
    topic_state = _get_or_create_topic_state(topic_id, state)
    return guid in topic_state.get("slack_sent", [])


def mark_topic_slack_sent(topic_id, guid, state):
    """Mark a GUID as sent to Slack for a specific topic."""
    topic_state = _get_or_create_topic_state(topic_id, state)

    if "slack_sent" not in topic_state:
        topic_state["slack_sent"] = []

    if guid not in topic_state["slack_sent"]:
        topic_state["slack_sent"].append(guid)


def is_topic_sheets_logged(topic_id, guid, state):
    """Check if a GUID has been logged to Google Sheets for a specific topic."""
    topic_state = _get_or_create_topic_state(topic_id, state)
    return guid in topic_state.get("sheets_logged", [])


def mark_topic_sheets_logged(topic_id, guid, state):
    """Mark a GUID as logged to Google Sheets for a specific topic."""
    topic_state = _get_or_create_topic_state(topic_id, state)

    if "sheets_logged" not in topic_state:
        topic_state["sheets_logged"] = []

    if guid not in topic_state["sheets_logged"]:
        topic_state["sheets_logged"].append(guid)


def get_topic_state(topic_id, state):
    """Get the state for a specific topic."""
    return _get_or_create_topic_state(topic_id, state)


def initialize_topic_state(topic_id, state):
    """Initialize an empty state for a new topic."""
    _get_or_create_topic_state(topic_id, state)
    return state
