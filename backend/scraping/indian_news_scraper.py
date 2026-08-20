import re
import urllib.parse
import feedparser
from typing import List, Dict, Any

COMPANY_SEARCH_TERMS = {
    "sbin.ns": "State Bank of India stock",
    "sbin": "State Bank of India stock",
    "sbi": "State Bank of India stock",
    "reliance.ns": "Reliance Industries stock",
    "reliance": "Reliance Industries stock",
    "tcs.ns": "Tata Consultancy Services stock",
    "tcs": "Tata Consultancy Services stock",
    "hdfcbank.ns": "HDFC Bank stock",
    "hdfcbank": "HDFC Bank stock",
    "icicibank.ns": "ICICI Bank stock",
    "infy.ns": "Infosys stock",
    "aapl": "Apple stock",
    "tsla": "Tesla stock",
    "nvda": "Nvidia stock",
    "msft": "Microsoft stock",
    "googl": "Alphabet Google stock"
}

KEYWORD_MAP = {
    "sbin.ns": ["sbi", "state bank of india", "sbin", "bank"],
    "sbin": ["sbi", "state bank of india", "sbin", "bank"],
    "sbi": ["sbi", "state bank of india", "sbin", "bank"],
    "reliance.ns": ["reliance", "ril", "ambani", "jio"],
    "reliance": ["reliance", "ril", "ambani", "jio"],
    "tcs.ns": ["tcs", "tata consultancy", "tata"],
    "hdfcbank.ns": ["hdfc", "hdfc bank", "hdfcbank"],
    "aapl": ["apple", "aapl", "iphone", "tim cook"],
    "tsla": ["tesla", "tsla", "elon musk"],
    "nvda": ["nvidia", "nvda", "jensen huang"]
}

def fetch_indian_financial_news(ticker: str, limit: int = 12) -> List[Dict[str, Any]]:
    """
    Fetches articles specifically relevant to the requested company by querying
    company-targeted search feeds and strictly enforcing keyword containment.
    """
    clean_ticker = ticker.upper().strip()
    raw_query = ticker.strip().lower()

    # 1. Determine company search term
    search_term = COMPANY_SEARCH_TERMS.get(raw_query) or COMPANY_SEARCH_TERMS.get(raw_query.split('.')[0])
    if not search_term:
        clean_symbol = clean_ticker.replace(".NS", "").replace(".BO", "")
        search_term = f"{clean_symbol} stock india"

    keywords = KEYWORD_MAP.get(raw_query) or KEYWORD_MAP.get(raw_query.split('.')[0])
    if not keywords:
        clean_sym = clean_ticker.replace(".NS", "").replace(".BO", "").lower()
        keywords = [clean_sym]

    matched_articles: List[Dict[str, Any]] = []
    seen_titles = set()

    # Query Targeted Search Feeds (Google News Company RSS & Publisher RSS)
    q_encoded = urllib.parse.quote(search_term)
    feeds = [
        ("Targeted Company News", f"https://news.google.com/rss/search?q={q_encoded}&hl=en-IN&gl=IN&ceid=IN:en"),
        ("Moneycontrol Latest", "https://www.moneycontrol.com/rss/latestnews.xml"),
        ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms"),
        ("LiveMint Companies", "https://www.livemint.com/rss/companies")
    ]

    for source_label, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                link = entry.get("link", "")
                pub_date = entry.get("published", "Recent")
                source_name = entry.get("source", {}).get("title", source_label)

                content_blob = f"{title} {summary}".lower()

                # Containment check: Title or summary must explicitly mention company keywords
                if any(re.search(r'\b' + re.escape(kw) + r'\b', content_blob) or kw in content_blob for kw in keywords):
                    # Clean title formatting
                    clean_title = title
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        clean_title = parts[0]
                        if source_name == source_label or not source_name:
                            source_name = parts[1]

                    norm_t = clean_title.lower()
                    if norm_t not in seen_titles and len(clean_title) > 10:
                        seen_titles.add(norm_t)
                        matched_articles.append({
                            "ticker": clean_ticker,
                            "title": clean_title,
                            "description": summary,
                            "link": link,
                            "url": link,
                            "published_at": pub_date,
                            "source": source_name,
                            "scraper": "indian_news_scraper"
                        })
        except Exception as e:
            print(f"[Scraper] Error parsing {source_label} feed ({feed_url}): {e}")

    return matched_articles[:limit]
