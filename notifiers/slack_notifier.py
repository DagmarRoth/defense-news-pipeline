"""Slack notification integration for sending high-priority defense news alerts."""

import requests
from typing import Dict, Any


def format_slack_message(item: Dict[str, Any], topic_name: str = None) -> Dict[str, str]:
    """
    Format an analyzed news item into a Slack message.

    Args:
        item: Analyzed item with title, link, analysis (score, summary, why), etc.
        topic_name: Optional topic name to include in the header

    Returns:
        Dictionary with 'text' key for Slack message
    """
    analysis = item.get("analysis", {})
    score = analysis.get("score", 0)
    summary = analysis.get("summary", "No summary available")
    why = analysis.get("why", "")
    title = item.get("title", "Untitled")
    link = item.get("link", "")
    item_type = item.get("type", "unknown").upper()

    # Truncate long text
    title_short = title[:80]
    summary_short = summary[:200]
    why_short = why[:150] + "..." if len(why) > 150 else why

    # Build header with optional topic
    if topic_name:
        header = f"🚨 *{topic_name}* - High-Priority Alert ({item_type})"
    else:
        header = f"🚨 *High-Priority Defense News Alert* ({item_type})"

    # Format as plain text message
    message_text = f"""{header}
*Score:* {score}/10

*Title:* {title_short}

*Summary:* {summary_short}

*Why Newsworthy:* {why_short}

🔗 Read More: {link}"""

    return {"text": message_text}


def is_notification_worthy(item: Dict[str, Any], threshold: int = 6) -> bool:
    """
    Check if an item meets the score threshold for notification.

    Args:
        item: Analyzed item
        threshold: Minimum score to trigger notification (default 6)

    Returns:
        True if score >= threshold, False otherwise
    """
    analysis = item.get("analysis", {})
    score = analysis.get("score", 0)
    return score >= threshold


def send_slack_notification(webhook_url: str, item: Dict[str, Any], topic_name: str = None) -> bool:
    """
    Send a notification to Slack via webhook.

    Args:
        webhook_url: Slack incoming webhook URL
        item: Analyzed news item to send
        topic_name: Optional topic name to include in message

    Returns:
        True if successful, False otherwise
    """
    try:
        message = format_slack_message(item, topic_name=topic_name)
        response = requests.post(webhook_url, json=message, timeout=10)

        if response.status_code == 200:
            title = item.get("title", "")[:50]
            score = item.get("analysis", {}).get("score", 0)
            print(f"  ✓ Slack notified: {title}... (Score: {score}/10)")
            return True
        else:
            print(f"  ✗ Slack notification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error sending Slack notification: {e}")
        return False
