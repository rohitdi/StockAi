import urllib.parse
import requests
from typing import Optional, Callable
from backend.db.database import db_client

FILLER_WORDS = [
    "stock", "shares", "share", "price of", "price for", "price",
    "sentiment for", "sentiment on", "sentiment about", "sentiment",
    "news on", "news about", "news for", "news", "quote for", "quote of",
    "latest on", "latest for"
]

FALLBACK_ALIASES = {
    "sbi": "SBIN.NS",
    "sbi stock": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "reliance": "RELIANCE.NS",
    "reliance stock": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "tata consultancy services": "TCS.NS",
    "infosys": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "tata motors": "TATAMOTORS.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS"
}

SUFFIX_FALLBACKS = [".NS", ".BO", ".L", ".TO"]

def clean_query(raw_query: str) -> str:
    q = raw_query.lower()
    for word in FILLER_WORDS:
        q = q.replace(word, "")
    cleaned = q.strip()
    return cleaned if cleaned else raw_query.strip()

def yahoo_search_resolve(query: str) -> Optional[str]:
    if not query:
        return None
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(url, params={"q": query, "quotesCount": 5}, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            equities = [q for q in quotes if q.get("quoteType") == "EQUITY"]
            if equities:
                return equities[0].get("symbol")
            if quotes:
                return quotes[0].get("symbol")
    except Exception as e:
        print(f"[TickerResolver] Yahoo search suggest request failed for '{query}': {e}")
    return None

def resolve_ticker(raw_query: str) -> Optional[str]:
    if not raw_query or not raw_query.strip():
        return None

    raw_clean = raw_query.strip()
    cached = db_client.get_ticker_resolution(raw_clean)
    if cached:
        return cached

    cleaned = clean_query(raw_clean)
    if not cleaned:
        return None

    resolved = FALLBACK_ALIASES.get(cleaned.lower()) or FALLBACK_ALIASES.get(raw_clean.lower())

    if not resolved:
        resolved = yahoo_search_resolve(cleaned)

    if not resolved:
        resolved = cleaned.upper()

    if resolved:
        db_client.save_ticker_resolution(raw_clean, resolved)

    return resolved

def resolve_with_exchange_fallback(ticker: str, fetch_fn: Callable[[str], bool]) -> Optional[str]:
    if fetch_fn(ticker):
        return ticker
        
    base = ticker.split(".")[0]
    for suffix in SUFFIX_FALLBACKS:
        candidate = f"{base}{suffix}"
        if fetch_fn(candidate):
            return candidate
            
    return None
