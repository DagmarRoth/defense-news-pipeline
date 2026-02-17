import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DVIDSHUB NEWS PIPELINE - Part 2: Claude Analysis
# ============================================================================
# This script reads scraped news/video items and uses Claude to assess
# newsworthiness, summarize content, and explain why items matter.
# ============================================================================

# Configuration
CURRENT_ITEMS_FILE = Path('data/current_items.json')
ANALYZED_FILE = Path('data/analyzed_items.json')

# Initialize Claude client (uses ANTHROPIC_API_KEY from environment)
client = Anthropic()

# System prompt - tells Claude how to behave
SYSTEM_PROMPT = """You are a defense news editor filtering content from DVIDS (Defense Visual Information Distribution Service) for a newsroom.

Your job is to assess whether each news item or video is newsworthy and interesting.

FOCUS AREA: Broad US military news, with special attention to breaking news, incidents, conflicts, and operations.

WHAT'S NEWSWORTHY:
- Real incidents: conflicts, rescues, military operations, strategic moves
- Breaking developments: command changes, policy shifts, significant events
- Visual stories: videos of interesting military operations or events

WHAT'S ROUTINE (usually not newsworthy):
- Routine training exercises (unless something went wrong or it's unusual)
- Personnel promotions/ceremonies (unless the person is very senior)
- Administrative updates
- Ribbon cuttings, base anniversaries, holiday events

For each item, respond with EXACTLY this JSON format:
{
    "newsworthy": true/false,
    "score": 1-10 (10 = must-read, 1 = skip),
    "summary": "1-2 sentence summary of what this is about",
    "why": "Why this is/isn't newsworthy - what's interesting or routine about it?"
}

Be concise. Think like a news editor: would this make a good story or is it routine?"""


def load_items_to_analyze():
    """Load items from scraper output."""
    if not CURRENT_ITEMS_FILE.exists():
        print(f"ERROR: {CURRENT_ITEMS_FILE} not found. Run scraper.py first.")
        return None

    with open(CURRENT_ITEMS_FILE, 'r') as f:
        data = json.load(f)

    return data.get('items', [])


def analyze_item_with_claude(item):
    """Send an item to Claude for analysis."""

    # Build a prompt for this specific item
    item_text = f"""
Item Type: {item['type'].upper()}
Title: {item['title']}
Author: {item['author']}
Published: {item['published']}
Link: {item['link']}

Description: {item['description']}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze this defense news item:\n{item_text}"
                }
            ]
        )

        # Parse Claude's response
        response_text = message.content[0].text

        # Try to extract JSON from response
        try:
            # If Claude returns valid JSON, parse it
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks (```json ... ```)
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    # Fallback if still can't parse
                    analysis = {
                        "newsworthy": False,
                        "score": 1,
                        "summary": "Could not parse analysis",
                        "why": "Error analyzing item"
                    }
            else:
                # Fallback if response isn't JSON or code block
                analysis = {
                    "newsworthy": False,
                    "score": 1,
                    "summary": "Could not parse analysis",
                    "why": "Error analyzing item"
                }

        return analysis

    except Exception as e:
        print(f"  ERROR analyzing item: {e}")
        return {
            "newsworthy": False,
            "score": 0,
            "summary": "Analysis failed",
            "why": str(e)
        }


def analyze_all_items(items):
    """Analyze all items using Claude."""
    analyzed = []

    print("\n" + "="*70)
    print("DVIDSHUB CONTENT ANALYZER")
    print("="*70)
    print(f"Analyzing {len(items)} items with Claude...\n")

    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['type'].upper()}: {item['title'][:50]}...", end=" → ")

        analysis = analyze_item_with_claude(item)

        # Combine original item with analysis
        analyzed_item = {
            **item,
            "analysis": analysis,
            "analyzed_at": datetime.now().isoformat()
        }

        analyzed.append(analyzed_item)

        # Show result
        score = analysis.get('score', 0)
        newsworthy = analysis.get('newsworthy', False)
        emoji = "⭐" if newsworthy else "○"
        print(f"{emoji} Score: {score}/10")

    return analyzed


def save_analyzed_items(analyzed_items):
    """Save analyzed items to JSON."""
    output = {
        "last_updated": datetime.now().isoformat(),
        "total_items": len(analyzed_items),
        "newsworthy_count": sum(1 for item in analyzed_items if item['analysis'].get('newsworthy')),
        "items": analyzed_items
    }

    with open(ANALYZED_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(analyzed_items)} analyzed items to {ANALYZED_FILE}")


def main():
    """Main execution."""
    try:
        # Load items from scraper
        items = load_items_to_analyze()
        if not items:
            print("No items to analyze.")
            return

        print(f"Loaded {len(items)} items from scraper output")

        # Analyze with Claude
        analyzed_items = analyze_all_items(items)

        # Save results
        save_analyzed_items(analyzed_items)

        print("\n" + "="*70)
        print("Analysis complete!")
        print("="*70)
        print(f"\nResults saved. Next step: Format output for newsroom (Part 3)")

    except Exception as e:
        print(f"\nERROR: {e}")
        raise


if __name__ == '__main__':
    main()
