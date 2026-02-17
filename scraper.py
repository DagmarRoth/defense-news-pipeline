import requests
import json
import re
import warnings
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress the XML-as-HTML warning - we know what we're doing
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ============================================================================
# DVIDSHUB NEWS PIPELINE - Part 1: Data Collection
# ============================================================================
# This script fetches the latest news and videos from DVIDS, tracks what's
# new, and stores the results for analysis in Part 2.
# ============================================================================

# Configuration
RSS_FEEDS = {
    'news': 'https://www.dvidshub.net/rss/news',
    'video': 'https://www.dvidshub.net/rss/video',
}

# Files we'll store data in
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

CURRENT_ITEMS_FILE = DATA_DIR / 'current_items.json'
PROCESSED_FILE = DATA_DIR / '.processed_guids.json'  # Hidden file to track what we've seen

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def load_processed_guids():
    """Load the list of GUIDs we've already processed."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_processed_guids(guids):
    """Save the list of processed GUIDs."""
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(guids), f)


def parse_rss_feed(feed_url, feed_type):
    """Fetch and parse an RSS feed."""
    print(f"  Fetching {feed_type} feed...")

    try:
        response = requests.get(feed_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR fetching {feed_type} feed: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    items = soup.find_all('item')

    parsed_items = []
    for item in items:
        try:
            # Extract data from RSS item
            title = item.find('title')
            title_text = title.get_text(strip=True) if title else "No title"

            # Try multiple ways to find pubDate (case variations due to HTML parser)
            pub_date_text = ""
            for tag_name in ['pubdate', 'pubDate', 'pubdate', 'pubDate']:
                pub_date = item.find(tag_name)
                if pub_date:
                    pub_date_text = pub_date.get_text(strip=True)
                    break

            description = item.find('description')
            desc_text = description.get_text() if description else ""  # Keep HTML for link extraction

            # Extract link - try RSS link tag first, then HTML in description
            link_url = ""
            link = item.find('link')
            if link and link.string:
                link_url = link.string.strip()

            # If no link, extract from description HTML
            if not link_url:
                href_match = re.search(r'href=[\'"]([^\'"]*dvidshub\.net[^\'"]*)[\'"]', desc_text)
                if href_match:
                    link_url = href_match.group(1)

            guid = item.find('guid')
            guid_text = guid.get_text(strip=True) if guid else ""

            author = item.find('author')
            author_text = author.get_text(strip=True) if author else "Unknown"

            # Look for thumbnail/media (try both namespace and non-namespace variants)
            thumbnail = item.find('media:thumbnail') or item.find('thumbnail')
            thumbnail_url = thumbnail.get('url', '') if thumbnail else ""

            # Clean up description - remove HTML tags
            desc_clean = re.sub(r'<[^>]+>', '', desc_text).strip()

            parsed_item = {
                'type': feed_type,
                'title': title_text,
                'link': link_url,
                'published': pub_date_text,
                'description': desc_clean,
                'guid': guid_text,
                'author': author_text,
                'thumbnail': thumbnail_url,
                'fetched_at': datetime.now().isoformat(),
            }

            parsed_items.append(parsed_item)
        except Exception as e:
            print(f"    Warning: Could not parse item: {e}")
            continue

    print(f"  Found {len(parsed_items)} {feed_type} items")
    return parsed_items


def fetch_all_content():
    """Fetch content from all RSS feeds."""
    print("\n" + "="*70)
    print("DVIDSHUB CONTENT SCRAPER")
    print("="*70)
    print(f"Starting fetch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_items = []

    # Fetch from each feed
    for feed_type, feed_url in RSS_FEEDS.items():
        items = parse_rss_feed(feed_url, feed_type)
        all_items.extend(items)

    print(f"\nTotal items fetched: {len(all_items)}")

    return all_items


def identify_new_items(all_items):
    """Identify which items are new based on GUID tracking."""
    processed_guids = load_processed_guids()

    new_items = []
    for item in all_items:
        if item['guid'] not in processed_guids:
            new_items.append(item)

    print(f"New items (not seen before): {len(new_items)}")

    # Update processed GUIDs
    for item in all_items:
        processed_guids.add(item['guid'])
    save_processed_guids(processed_guids)

    return new_items


def save_current_items(items):
    """Save current items to JSON file."""
    # Prepare for JSON (convert any non-serializable items)
    output = {
        'last_updated': datetime.now().isoformat(),
        'total_items': len(items),
        'items': items
    }

    with open(CURRENT_ITEMS_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(items)} items to {CURRENT_ITEMS_FILE}")


def main():
    """Main execution. Scrapes DVIDS and returns new items found."""
    try:
        # Step 1: Fetch all content
        all_items = fetch_all_content()

        # Step 2: Identify what's new
        new_items = identify_new_items(all_items)

        # Step 3: Save for later processing
        save_current_items(new_items)

        print("\n" + "="*70)
        print("Scraping complete!")
        print("="*70)
        print(f"\nNext step: Run Claude analysis on these items (Part 2)")

        return new_items

    except Exception as e:
        print(f"\nERROR: {e}")
        raise


if __name__ == '__main__':
    main()
