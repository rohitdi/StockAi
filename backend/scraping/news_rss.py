import urllib.parse
import feedparser
from typing import List, Dict, Any

def fetch_google_news_rss(ticker: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Primary news scraper: Google News RSS feed for given stock ticker.
    Public, unauthenticated XML endpoint with reliable performance.
    """
    clean_ticker = ticker.strip().upper()
    query = urllib.parse.quote(f"{clean_ticker} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        feed = feedparser.parse(url)
        headlines = []
        
        for entry in feed.entries[:limit]:
            pub_date = entry.get("published", "")
            title = entry.get("title", "")
            link = entry.get("link", "")
            source = entry.get("source", {}).get("title", "Google News")
            
            clean_title = title
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                clean_title = parts[0]
                if not source or source == "Google News":
                    source = parts[1]

            headlines.append({
                "ticker": clean_ticker,
                "title": clean_title,
                "link": link,
                "published_at": pub_date,
                "source": source,
                "scraper": "google_news_rss"
            })
            
        return headlines
    except Exception as e:
        print(f"[Scraper] RSS error for {ticker}: {e}")
        return []
