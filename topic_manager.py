"""
Topic Management System for DVIDS Pipeline

Handles CRUD operations for user-defined monitoring topics.
Topics are now stored in Google Sheets for shared access between web and worker services.
"""

import os
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional
import gspread


# Initialize Google Sheets client
def _get_sheets_client():
    """Get authenticated Google Sheets client."""
    try:
        from app import SHEETS_CLIENT  # Import from app where it's initialized
        if SHEETS_CLIENT is None:
            raise RuntimeError("SHEETS_CLIENT is None in app.py")
        return SHEETS_CLIENT
    except (ImportError, AttributeError, RuntimeError):
        # Fallback: initialize directly if running independently
        from pathlib import Path

        credentials_file = Path('credentials/google_service_account.json')
        if not credentials_file.exists():
            raise RuntimeError("Google credentials not found at credentials/google_service_account.json")

        return gspread.service_account(filename=str(credentials_file))


def _get_topics_worksheet():
    """Get or create the Topics worksheet in the main spreadsheet."""
    client = _get_sheets_client()
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')

    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID environment variable not set. Please set it in Railway environment variables.")

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except gspread.SpreadsheetNotFound as e:
        raise RuntimeError(f"Spreadsheet {spreadsheet_id} not found. Check that GOOGLE_SHEETS_SPREADSHEET_ID is correct and the service account has access.") from e
    except Exception as e:
        raise RuntimeError(f"Error accessing spreadsheet: {e}") from e

    # Try to get existing Topics worksheet
    try:
        worksheet = spreadsheet.worksheet('Topics')
    except gspread.WorksheetNotFound:
        # Create Topics worksheet with headers
        try:
            worksheet = spreadsheet.add_worksheet('Topics', rows=1000, cols=10)
            headers = ['ID', 'Name', 'Keywords', 'Sheet_ID', 'Sheet_Name', 'Slack_Webhook', 'Score_Threshold', 'Active', 'Created_At', 'Updated_At']
            worksheet.append_row(headers)
        except Exception as e:
            raise RuntimeError(f"Error creating Topics worksheet: {e}") from e

    return worksheet


def _row_to_topic(row: List) -> Optional[Dict]:
    """Convert a worksheet row to a topic dictionary."""
    if not row or len(row) < 8:
        return None

    try:
        return {
            'id': row[0],
            'name': row[1],
            'keywords': [k.strip().lower() for k in row[2].split(',') if k.strip()],
            'sheet_id': row[3],
            'sheet_name': row[4],
            'slack_webhook': row[5] if row[5] else None,
            'score_threshold': int(row[6]) if row[6] else 5,
            'active': row[7].lower() == 'true' if row[7] else True,
            'created_at': row[8] if len(row) > 8 else '',
            'updated_at': row[9] if len(row) > 9 else ''
        }
    except (ValueError, IndexError):
        return None


def _topic_to_row(topic: Dict) -> List:
    """Convert a topic dictionary to a worksheet row."""
    return [
        topic['id'],
        topic['name'],
        ','.join(topic['keywords']),
        topic['sheet_id'],
        topic['sheet_name'],
        topic.get('slack_webhook', ''),
        str(topic.get('score_threshold', 5)),
        'true' if topic.get('active', True) else 'false',
        topic.get('created_at', ''),
        topic.get('updated_at', '')
    ]


def load_topics() -> List[Dict]:
    """Load all topics from Google Sheets."""
    try:
        worksheet = _get_topics_worksheet()
        rows = worksheet.get_all_values()

        # Skip header row
        topics = []
        for row in rows[1:]:
            topic = _row_to_topic(row)
            if topic:
                topics.append(topic)

        return topics
    except Exception as e:
        print(f"Error loading topics from Sheets: {e}")
        return []


def save_topics(topics: List[Dict]) -> None:
    """
    Save topics to Google Sheets.

    Note: This function is kept for compatibility but is not used directly.
    Individual CRUD operations update Sheets directly.
    """
    try:
        worksheet = _get_topics_worksheet()
        # Clear all data rows (keep header)
        worksheet.delete_rows(2, worksheet.row_count)

        # Write all topics
        for topic in topics:
            worksheet.append_row(_topic_to_row(topic))
    except Exception as e:
        print(f"Error saving topics to Sheets: {e}")
        raise


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
    Create a new topic and save it to Google Sheets.

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

    # Add to Sheets
    try:
        worksheet = _get_topics_worksheet()
        worksheet.append_row(_topic_to_row(topic))
    except Exception as e:
        raise RuntimeError(f"Failed to create topic in Google Sheets: {e}")

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
    Update a topic's fields in Google Sheets.

    Args:
        topic_id: ID of topic to update
        **updates: Fields to update (e.g., name='New Name', active=False)

    Returns:
        Updated topic or None if not found
    """
    try:
        worksheet = _get_topics_worksheet()
        rows = worksheet.get_all_values()

        # Find the topic row
        topic_row_idx = None
        for idx, row in enumerate(rows[1:], start=2):
            if row and row[0] == topic_id:
                topic_row_idx = idx
                break

        if topic_row_idx is None:
            return None

        # Convert row to topic
        topic = _row_to_topic(rows[topic_row_idx - 1])
        if not topic:
            return None

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

        # Update the row in Sheets
        row_data = _topic_to_row(topic)
        print(f"  Updating row {topic_row_idx} with data: {row_data}")
        worksheet.update_values(f'A{topic_row_idx}:J{topic_row_idx}', [row_data])
        print(f"  ✓ Row updated successfully")
        return topic

    except Exception as e:
        print(f"Error updating topic {topic_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def delete_topic(topic_id: str) -> bool:
    """
    Delete a topic by marking it inactive in Google Sheets.

    Args:
        topic_id: ID of topic to delete

    Returns:
        True if deleted, False if not found
    """
    print(f"Deleting topic {topic_id}...")
    result = update_topic(topic_id, active=False)
    if result:
        print(f"✓ Topic '{result['name']}' marked as inactive")
        return True
    else:
        print(f"✗ Failed to delete topic {topic_id}")
        return False


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
    print("Testing topic_manager.py (Google Sheets backend)...")

    try:
        # Load existing topics
        topics = load_topics()
        print(f"✓ Loaded {len(topics)} existing topics from Google Sheets")

        # List active
        active = list_active_topics()
        print(f"✓ Active topics: {len(active)}")

        # Get first topic if available
        if active:
            first = active[0]
            print(f"✓ Sample topic: {first['name']} with keywords: {first['keywords']}")

        print("\nGoogle Sheets backend is working!")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("Make sure GOOGLE_SHEETS_SPREADSHEET_ID is set and Google credentials are available")
