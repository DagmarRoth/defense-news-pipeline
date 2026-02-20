"""
Topic Management System for DVIDS Pipeline

Handles CRUD operations for user-defined monitoring topics.
Topics are stored in JSON format for simplicity and version control.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional


TOPICS_FILE = Path('data/topics.json')


def ensure_topics_file():
    """Create topics.json if it doesn't exist."""
    TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TOPICS_FILE.exists():
        save_topics([])


def load_topics() -> List[Dict]:
    """Load all topics from JSON file."""
    ensure_topics_file()
    try:
        with open(TOPICS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_topics(topics: List[Dict]) -> None:
    """
    Save topics to JSON file with atomic write.

    Writes to temporary file first, then renames to prevent corruption
    if write is interrupted.
    """
    # Ensure directory exists
    TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    temp_file = TOPICS_FILE.with_suffix('.json.tmp')
    try:
        with open(temp_file, 'w') as f:
            json.dump(topics, f, indent=2)

        # Atomic rename (works on most filesystems)
        temp_file.replace(TOPICS_FILE)
    except Exception as e:
        # Clean up temp file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise e


def validate_topic(topic: Dict) -> tuple[bool, str]:
    """
    Validate topic data structure.

    Returns (is_valid, error_message)
    """
    required_fields = ['name', 'keywords', 'sheet_id', 'sheet_name']

    for field in required_fields:
        if field not in topic or not topic[field]:
            return False, f"Missing required field: {field}"

    if not isinstance(topic['keywords'], list) or len(topic['keywords']) == 0:
        return False, "Keywords must be a non-empty list"

    if not isinstance(topic['name'], str) or len(topic['name'].strip()) == 0:
        return False, "Topic name must be a non-empty string"

    score_threshold = topic.get('score_threshold', 5)
    if not isinstance(score_threshold, int) or score_threshold < 1 or score_threshold > 10:
        return False, "Score threshold must be between 1 and 10"

    return True, ""


def create_topic(
    name: str,
    keywords: List[str],
    sheet_id: str,
    sheet_name: str,
    slack_webhook: Optional[str] = None,
    score_threshold: int = 5
) -> Dict:
    """
    Create a new topic and save it.

    Args:
        name: Human-readable topic name
        keywords: List of keywords to match
        sheet_id: Google Sheets spreadsheet ID
        sheet_name: Worksheet name within spreadsheet
        slack_webhook: Optional Slack webhook URL
        score_threshold: Minimum score for alerts (1-10, default 5)

    Returns:
        Created topic dictionary with ID and timestamp
    """
    topic = {
        "id": str(uuid4()),
        "name": name.strip(),
        "keywords": [k.strip().lower() for k in keywords if k.strip()],
        "sheet_id": sheet_id,
        "sheet_name": sheet_name[:100],  # Google Sheets worksheet name limit
        "slack_webhook": slack_webhook,
        "score_threshold": score_threshold,
        "active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Validate before saving
    is_valid, error = validate_topic(topic)
    if not is_valid:
        raise ValueError(f"Invalid topic: {error}")

    # Add to list and save
    topics = load_topics()
    topics.append(topic)
    save_topics(topics)

    return topic


def get_topic_by_id(topic_id: str) -> Optional[Dict]:
    """Get a specific topic by ID."""
    topics = load_topics()
    for topic in topics:
        if topic['id'] == topic_id:
            return topic
    return None


def update_topic(topic_id: str, **updates) -> Optional[Dict]:
    """
    Update a topic's fields.

    Args:
        topic_id: ID of topic to update
        **updates: Fields to update (e.g., name='New Name', active=False)

    Returns:
        Updated topic or None if not found
    """
    topics = load_topics()

    for i, topic in enumerate(topics):
        if topic['id'] == topic_id:
            # Update allowed fields only
            allowed_fields = ['name', 'keywords', 'slack_webhook', 'score_threshold', 'active']
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'keywords' and isinstance(value, list):
                        topic[field] = [k.strip().lower() for k in value if k.strip()]
                    else:
                        topic[field] = value

            topic['updated_at'] = datetime.now().isoformat()

            # Validate after update
            is_valid, error = validate_topic(topic)
            if not is_valid:
                raise ValueError(f"Invalid update: {error}")

            topics[i] = topic
            save_topics(topics)
            return topic

    return None


def delete_topic(topic_id: str) -> bool:
    """
    Delete a topic by marking it inactive.

    Args:
        topic_id: ID of topic to delete

    Returns:
        True if deleted, False if not found
    """
    result = update_topic(topic_id, active=False)
    return result is not None


def list_active_topics() -> List[Dict]:
    """Get all active topics."""
    topics = load_topics()
    return [topic for topic in topics if topic.get('active', True)]


def list_all_topics() -> List[Dict]:
    """Get all topics including inactive ones."""
    return load_topics()


def get_topic_sheet_url(topic: Dict) -> str:
    """Generate Google Sheets URL for a topic."""
    return f"https://docs.google.com/spreadsheets/d/{topic['sheet_id']}"


if __name__ == '__main__':
    # Quick test
    print("Testing topic_manager.py...")

    # Create a test topic
    test_topic = create_topic(
        name="Test Topic",
        keywords=["test", "demo"],
        sheet_id="test-sheet-id",
        sheet_name="Test"
    )
    print(f"✓ Created topic: {test_topic['id']}")

    # Load and verify
    loaded = get_topic_by_id(test_topic['id'])
    print(f"✓ Retrieved topic: {loaded['name']}")

    # Update
    updated = update_topic(test_topic['id'], name="Updated Test Topic")
    print(f"✓ Updated topic: {updated['name']}")

    # List active
    active = list_active_topics()
    print(f"✓ Active topics: {len(active)}")

    # Delete
    deleted = delete_topic(test_topic['id'])
    print(f"✓ Deleted topic: {deleted}")

    print("\nAll tests passed!")
