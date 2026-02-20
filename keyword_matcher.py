"""
Keyword Matching Engine for Topic Filtering

Matches analyzed DVIDS items against topic keywords to determine
which topics an item belongs to.
"""

from typing import List, Dict


def matches_topic(item: Dict, keywords: List[str]) -> bool:
    """
    Check if an item matches ANY keyword from a topic.

    Performs case-insensitive substring matching on:
    - title
    - description
    - analysis.summary

    Args:
        item: Analyzed item dict with title, description, analysis
        keywords: List of lowercase keywords to match

    Returns:
        True if item matches any keyword
    """
    if not keywords:
        return False

    # Build searchable text from multiple fields
    searchable_text = ""

    if 'title' in item and item['title']:
        searchable_text += item['title'] + " "

    if 'description' in item and item['description']:
        searchable_text += item['description'] + " "

    if 'analysis' in item and 'summary' in item['analysis']:
        searchable_text += item['analysis']['summary'] + " "

    # Normalize: lowercase and remove extra whitespace
    searchable_text = searchable_text.lower().strip()

    # Check if any keyword appears in the searchable text
    for keyword in keywords:
        if keyword.lower() in searchable_text:
            return True

    return False


def filter_items_by_topic(items: List[Dict], topic: Dict) -> List[Dict]:
    """
    Filter items to only those matching a topic's keywords and score threshold.

    Args:
        items: List of analyzed items
        topic: Topic dict with keywords and score_threshold

    Returns:
        List of items that match the topic's criteria
    """
    if not items or not topic:
        return []

    keywords = topic.get('keywords', [])
    score_threshold = topic.get('score_threshold', 5)

    matching = []

    for item in items:
        # Must match keywords
        if not matches_topic(item, keywords):
            continue

        # Must meet score threshold
        score = item.get('analysis', {}).get('score', 0)
        if score < score_threshold:
            continue

        matching.append(item)

    return matching


def get_matching_topics(item: Dict, topics: List[Dict]) -> List[Dict]:
    """
    Find all topics that match a given item.

    Useful for understanding which topics are interested in an item.

    Args:
        item: Analyzed item to check
        topics: List of topic dicts to check against

    Returns:
        List of topics that match this item
    """
    if not item or not topics:
        return []

    matching_topics = []

    for topic in topics:
        if topic.get('active', True):  # Only check active topics
            if filter_items_by_topic([item], topic):
                matching_topics.append(topic)

    return matching_topics


def get_topic_statistics(items: List[Dict], topics: List[Dict]) -> Dict:
    """
    Generate statistics about item distribution across topics.

    Useful for monitoring and debugging.

    Args:
        items: List of analyzed items
        topics: List of topics

    Returns:
        Dict with statistics per topic
    """
    stats = {}

    for topic in topics:
        topic_id = topic['id']
        matching = filter_items_by_topic(items, topic)

        stats[topic_id] = {
            'name': topic['name'],
            'match_count': len(matching),
            'high_priority': sum(
                1 for item in matching
                if item.get('analysis', {}).get('score', 0) >= 8
            ),
            'keywords': topic['keywords']
        }

    return stats


if __name__ == '__main__':
    # Quick test
    print("Testing keyword_matcher.py...")

    # Create test item
    test_item = {
        'title': 'Nuclear Weapons Development in Iran',
        'description': 'New report on Iranian nuclear enrichment program',
        'analysis': {
            'score': 8,
            'newsworthy': True,
            'summary': 'Iran continues nuclear development despite sanctions'
        }
    }

    # Test matching
    keywords = ['nuclear', 'iran', 'weapons']
    result = matches_topic(test_item, keywords)
    print(f"✓ Item matches keywords: {result}")
    assert result == True, "Expected item to match keywords"

    # Test filtering with topic
    topic = {
        'id': 'test-topic',
        'name': 'Nuclear Development',
        'keywords': keywords,
        'score_threshold': 5,
        'active': True
    }

    items = [test_item]
    filtered = filter_items_by_topic(items, topic)
    print(f"✓ Filtered items: {len(filtered)} (expected 1)")
    assert len(filtered) == 1, "Expected 1 matching item"

    # Test with low score (should not match threshold)
    low_score_item = test_item.copy()
    low_score_item['analysis'] = {'score': 3}
    filtered_low = filter_items_by_topic([low_score_item], topic)
    print(f"✓ Low-score item filtered out: {len(filtered_low)} (expected 0)")
    assert len(filtered_low) == 0, "Expected low-score item to be filtered"

    # Test non-matching keywords
    no_match_item = {
        'title': 'New Base Opens in Germany',
        'description': 'Military installation news',
        'analysis': {'score': 7}
    }
    no_match = matches_topic(no_match_item, keywords)
    print(f"✓ Non-matching item excluded: {not no_match}")
    assert no_match == False, "Expected no match for unrelated item"

    print("\nAll tests passed!")
