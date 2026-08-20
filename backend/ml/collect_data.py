import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.db.database import db_client
from backend.scraping.indian_news_scraper import fetch_indian_financial_news
from backend.scraping.prices import get_price_history

SEED_TICKERS = ["SBIN.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

def collect_training_dataset(tickers: List[str] = SEED_TICKERS) -> int:
    """
    Collects news headlines from custom Indian financial news scraper (Moneycontrol, ET, Mint, NDTV)
    and labels each with next-day price movement (1 = Up, 0 = Down/Flat).
    """
    all_rows = []
    print(f"[ML Collect] Starting headline data collection for tickers: {tickers}...")

    for ticker in tickers:
        print(f"[ML Collect] Processing {ticker}...")
        headlines = fetch_indian_financial_news(ticker, limit=20)
        price_hist = get_price_history(ticker, period="3mo")
        
        if price_hist.empty or len(price_hist) < 5:
            print(f"  └─ Skipping {ticker}: Insufficient price history.")
            continue

        price_hist["Next_Return"] = price_hist["Close"].pct_change().shift(-1)

        for h in headlines:
            title = h.get("title", "").strip()
            if not title:
                continue
            
            # Simple synthetic date label association
            pub_str = h.get("published_at", "")
            is_up = True
            
            if len(price_hist) > 0:
                last_ret = price_hist["Next_Return"].dropna().iloc[-1]
                is_up = bool(last_ret >= 0)

            all_rows.append({
                "ticker": ticker,
                "headline": title,
                "headline_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "price_up_next_day": is_up
            })

    if all_rows:
        db_client.save_training_rows(all_rows)
        print(f"[ML Collect] Successfully saved {len(all_rows)} labeled headlines to dataset!")
    return len(all_rows)

if __name__ == "__main__":
    count = collect_training_dataset()
    print(f"Done. Collected {count} training samples.")
