"""Google Sheets integration for logging analyzed defense news items."""

import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any, List
import os


SHEETS_SCOPE = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_HEADERS = ['Timestamp', 'GUID', 'Type', 'Title', 'Score', 'Newsworthy', 'Summary', 'Why', 'Link']


def init_sheets_client(credentials_path: str) -> gspread.Client:
    """
    Initialize Google Sheets API client using service account credentials.

    Args:
        credentials_path: Path to service account JSON file

    Returns:
        Authenticated gspread client

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        Exception: If authentication fails
    """
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    try:
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=SHEETS_SCOPE
        )
        client = gspread.authorize(creds)
        print(f"✓ Google Sheets client initialized")
        return client

    except Exception as e:
        raise Exception(f"Failed to authenticate with Google Sheets: {e}")


def get_or_create_sheet(client: gspread.Client, spreadsheet_id: str) -> gspread.Worksheet:
    """
    Get existing worksheet or create new spreadsheet if needed.

    Args:
        client: Authenticated gspread client
        spreadsheet_id: Google Sheets spreadsheet ID

    Returns:
        Worksheet object for appending data

    Raises:
        Exception: If spreadsheet access fails
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet('Defense News')

        return worksheet

    except gspread.exceptions.WorksheetNotFound:
        # Worksheet doesn't exist, create it
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.add_worksheet(title='Defense News', rows='100', cols='9')

            # Add headers
            worksheet.append_row(SHEET_HEADERS)
            print(f"✓ Created new worksheet 'Defense News' with headers")

            return worksheet

        except Exception as e:
            raise Exception(f"Failed to create worksheet: {e}")

    except gspread.exceptions.SpreadsheetNotFound:
        raise Exception(f"Spreadsheet not found: {spreadsheet_id}. Check your GOOGLE_SHEETS_SPREADSHEET_ID.")

    except Exception as e:
        raise Exception(f"Failed to access Google Sheets: {e}")


def item_to_row(item: Dict[str, Any]) -> List[str]:
    """
    Convert analyzed item to a row for Google Sheets.

    Args:
        item: Analyzed news item

    Returns:
        List of strings for sheet row
    """
    analysis = item.get("analysis", {})

    row = [
        item.get("analyzed_at", "")[:19],  # Timestamp without microseconds
        item.get("guid", ""),
        item.get("type", "").upper(),
        item.get("title", "")[:200],  # Full title
        str(analysis.get("score", "")),
        str(analysis.get("newsworthy", False)),
        analysis.get("summary", "")[:400],  # Key summary points
        analysis.get("why", "")[:250],  # Brief explanation
        item.get("link", "")
    ]

    return row


def append_item_to_sheet(worksheet: gspread.Worksheet, item: Dict[str, Any]) -> bool:
    """
    Append a single analyzed item to the worksheet.

    Args:
        worksheet: gspread worksheet object
        item: Analyzed news item

    Returns:
        True if successful, False otherwise
    """
    try:
        row = item_to_row(item)
        worksheet.append_row(row)

        title = item.get("title", "")[:40]
        print(f"  ✓ Logged to Sheets: {title}...")
        return True

    except Exception as e:
        print(f"  ✗ Error logging to Sheets: {e}")
        return False


def batch_append_items_to_sheet(worksheet: gspread.Worksheet, items: List[Dict[str, Any]]) -> bool:
    """
    Append multiple analyzed items to the worksheet in a batch operation.

    Args:
        worksheet: gspread worksheet object
        items: List of analyzed news items

    Returns:
        True if successful, False otherwise
    """
    if not items:
        return True

    try:
        rows = [item_to_row(item) for item in items]
        worksheet.append_rows(rows)

        print(f"  ✓ Logged {len(items)} items to Sheets")
        return True

    except Exception as e:
        print(f"  ✗ Error batch logging to Sheets: {e}")
        return False
