import os
from typing import List, Dict, Any, Optional
from backend.db.database import db_client
from backend.scraping.news_rss import fetch_google_news_rss
from backend.scraping.html_fallback import fetch_google_html_fallback
from backend.scraping.prices import get_stock_summary, get_stock_chart_data
from backend.scraping.ticker_resolver import resolve_ticker, resolve_with_exchange_fallback

CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "30"))
HTML_SCRAPE_FALLBACK = os.getenv("HTML_SCRAPE_FALLBACK", "true").lower() in ("true", "1", "yes")

def get_cached_summary(raw_query: str) -> Optional[Dict[str, Any]]:
    resolved = resolve_ticker(raw_query)
    if not resolved:
        return None

    ticker = resolved.upper()
    
    # 1. Try DB cache first
    cached = db_client.get_cache(ticker, "summary", ttl_minutes=CACHE_TTL_MINUTES)
    if cached and isinstance(cached, dict):
        return cached

    # 2. Fetch fresh summary via yfinance, with exchange suffix fallback loop
    def _fetch_test(t: str) -> Optional[Dict[str, Any]]:
        return get_stock_summary(t)

    actual_ticker = resolve_with_exchange_fallback(ticker, lambda t: _fetch_test(t) is not None)
    if not actual_ticker:
        return None

    summary = get_stock_summary(actual_ticker)
    if summary:
        db_client.save_cache(summary["ticker"], "summary", summary)

    return summary

def get_cached_news(raw_query: str) -> List[Dict[str, Any]]:
    resolved = resolve_ticker(raw_query)
    if not resolved:
        return []

    ticker = resolved.upper()
    
    # 1. Try DB cache first
    cached = db_client.get_cache(ticker, "news", ttl_minutes=CACHE_TTL_MINUTES)
    if cached and isinstance(cached, list) and len(cached) > 0:
        return cached

    # 2. Scrape via Google News RSS (Primary)
    news = fetch_google_news_rss(ticker)
    
    # 3. Fallback to HTML search scraper if RSS empty and enabled
    if not news and HTML_SCRAPE_FALLBACK:
        print(f"[Cache] RSS returned zero items for {ticker}. Trying HTML fallback...")
        news = fetch_google_html_fallback(ticker)

    # 4. Save to cache if news found
    if news:
        db_client.save_cache(ticker, "news", news)
        
    return news

def get_cached_chart(raw_query: str, period: str = "1M") -> Optional[Dict[str, Any]]:
    resolved = resolve_ticker(raw_query)
    if not resolved:
        return None

    ticker = resolved.upper()
    period_clean = period.upper() if period else "1M"
    cache_source = f"chart_{period_clean}"

    # 1. Try DB cache first
    cached = db_client.get_cache(ticker, cache_source, ttl_minutes=CACHE_TTL_MINUTES)
    if cached and isinstance(cached, dict):
        return cached

    # 2. Fetch fresh chart data via yfinance
    chart_data = get_stock_chart_data(ticker, period=period_clean)
    if chart_data:
        db_client.save_cache(ticker, cache_source, chart_data)

    return chart_data
