import os
from typing import Optional, Dict, Any, List
from backend.db.database import db_client
from backend.scraping.prices import get_stock_summary, get_stock_chart_data
from backend.scraping.indian_news_scraper import fetch_indian_financial_news

CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "5"))

def get_cached_summary(ticker: str) -> Optional[Dict[str, Any]]:
    ticker = ticker.upper()
    cached = db_client.get_cache(ticker, source="summary", ttl_minutes=CACHE_TTL_MINUTES)
    if cached:
        return cached

    fresh = get_stock_summary(ticker)
    if fresh:
        db_client.save_cache(ticker, source="summary", payload=fresh)
    return fresh

def get_cached_chart(ticker: str, period: str = "1M") -> Optional[Dict[str, Any]]:
    ticker = ticker.upper()
    source_key = f"chart_{period.lower()}"
    cached = db_client.get_cache(ticker, source=source_key, ttl_minutes=CACHE_TTL_MINUTES)
    if cached:
        return cached

    fresh = get_stock_chart_data(ticker, period=period)
    if fresh:
        db_client.save_cache(ticker, source=source_key, payload=fresh)
    return fresh

def get_cached_news(ticker: str) -> List[Dict[str, Any]]:
    ticker = ticker.upper()
    cached = db_client.get_cache(ticker, source="indian_news_scraper", ttl_minutes=CACHE_TTL_MINUTES)
    if cached and isinstance(cached, list) and len(cached) > 0:
        return cached

    fresh = fetch_indian_financial_news(ticker)
    if fresh:
        db_client.save_cache(ticker, source="indian_news_scraper", payload=fresh)
        return fresh

    return []
