import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("="*70)
print("DVIDSHUB EXPLORATION - Version 2")
print("="*70)

# 1. Check for RSS feeds
print("\n1. LOOKING FOR RSS/FEED ENDPOINTS...")
print("-" * 70)

rss_urls_to_try = [
    "https://www.dvidshub.net/rss/news",
    "https://www.dvidshub.net/feed",
    "https://www.dvidshub.net/feeds",
    "https://www.dvidshub.net/rss",
]

for rss_url in rss_urls_to_try:
    try:
        resp = requests.get(rss_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            print(f"✓ Found RSS feed at: {rss_url}")
            soup = BeautifulSoup(resp.content, 'xml')
            items = soup.find_all('item')
            print(f"  Contains {len(items)} items")
            if items:
                print(f"  First item:")
                print(f"    Title: {items[0].find('title').get_text() if items[0].find('title') else 'N/A'}")
                print(f"    Link: {items[0].find('link').get_text() if items[0].find('link') else 'N/A'}")
            break
    except Exception as e:
        pass

# 2. Check the news search page
print("\n2. CHECKING NEWS SEARCH PAGE...")
print("-" * 70)

news_url = "https://www.dvidshub.net/search/2.0?type=news"
print(f"Fetching: {news_url}")

try:
    response = requests.get(news_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Look for news items
    print(f"Status code: {response.status_code}")

    # Find common news containers
    items = soup.find_all('article')
    if not items:
        items = soup.find_all(class_=re.compile(r'(news|article|story|item)', re.I))

    if items:
        print(f"Found {len(items)} potential news items")
        print("First item HTML preview:")
        print(str(items[0])[:800])
    else:
        print("No obvious news items found. Looking for divs with content...")
        # Try broader search
        divs = soup.find_all('div', class_=re.compile(r'content|post|story', re.I))
        if divs:
            print(f"Found {len(divs)} divs with content-like classes")
            print("First div preview:")
            print(str(divs[0])[:500])
        else:
            print("No clear news containers found.")
            print("\nPage structure snippet:")
            print(soup.prettify()[:1500])

except Exception as e:
    print(f"Error: {e}")

# 3. Check for JavaScript/API endpoints
print("\n3. LOOKING FOR API ENDPOINTS...")
print("-" * 70)

main_response = requests.get("https://www.dvidshub.net/", headers=headers, timeout=10)
main_soup = BeautifulSoup(main_response.content, 'html.parser')

# Look for script tags that might reveal API endpoints
scripts = main_soup.find_all('script')
print(f"Found {len(scripts)} script tags")

for script in scripts:
    if script.string:
        # Look for API URLs or endpoints
        if 'api' in script.string.lower() or 'fetch' in script.string.lower():
            print(f"Found potential API reference:")
            print(script.string[:300])
            break

print("\n" + "="*70)
