import requests
from bs4 import BeautifulSoup
import json

# Fetch the homepage
url = "https://www.dvidshub.net/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Fetching {url}...")
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()

# Parse the HTML
soup = BeautifulSoup(response.content, 'html.parser')

print("\n" + "="*60)
print("DVIDSHUB.NET STRUCTURE EXPLORATION")
print("="*60)

# Look for news/content items - common patterns
print("\n1. LOOKING FOR ARTICLE/NEWS CONTAINERS...")
print("-" * 60)

# Try different selectors that are common on news sites
selectors = [
    'article',
    '[class*="article"]',
    '[class*="post"]',
    '[class*="news"]',
    '[class*="item"]',
    'div[class*="release"]'
]

for selector in selectors:
    items = soup.select(selector)
    if items:
        print(f"Found {len(items)} elements matching '{selector}'")
        # Show first item structure
        if len(items) > 0:
            print(f"  First item HTML (first 500 chars):")
            print(f"  {str(items[0])[:500]}...")

print("\n2. LOOKING FOR LINKS TO NEWS/ARTICLES...")
print("-" * 60)

# Find all links that might be article links
links = soup.find_all('a', href=True)
article_links = [l for l in links if any(x in l.get('href', '').lower() for x in ['news', 'article', 'press', 'release', 'story'])]

if article_links:
    print(f"Found {len(article_links)} potential article links")
    print("First 5 examples:")
    for link in article_links[:5]:
        text = link.get_text(strip=True)[:60]
        href = link.get('href', '')
        print(f"  - {text}")
        print(f"    {href}")
else:
    print("No article-like links found. Showing all major links:")
    for link in links[:10]:
        text = link.get_text(strip=True)[:60]
        href = link.get('href', '')
        if text and len(text) > 3:
            print(f"  - {text}")
            print(f"    {href}")

print("\n3. PAGE TITLE & META INFO...")
print("-" * 60)
title = soup.find('title')
if title:
    print(f"Page title: {title.get_text()}")

meta_desc = soup.find('meta', attrs={'name': 'description'})
if meta_desc:
    print(f"Meta description: {meta_desc.get('content')}")

print("\n4. FULL PAGE STRUCTURE (first 1000 chars)...")
print("-" * 60)
print(soup.prettify()[:1000])

print("\n" + "="*60)
print("Exploration complete. Check output above to understand structure.")
print("="*60)
