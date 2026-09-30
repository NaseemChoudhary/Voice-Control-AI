import feedparser
import requests

# Feed sources with standard User-Agent header
NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",                  # Primary: BBC
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", # Fallback 1: NYT
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"   # Fallback 2: Google News
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_top_news(limit=3):
    """Fetch top news headlines from RSS feeds."""
    for url in NEWS_FEEDS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=5)

            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    return [entry.title for entry in feed.entries[:limit]]
        except Exception:
            continue

    return []