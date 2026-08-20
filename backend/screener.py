import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.cache import get_cached_summary, get_cached_news
from backend.ml.infer import predict_stock_sentiment
from backend.scraping.prices import get_price_history
from backend.scraping.ticker_resolver import resolve_ticker

SCORE_WEIGHTS = {
    "sentiment": 0.35,  # Headline sentiment model probability (0-100)
    "momentum": 0.25,   # Trailing 20-day price return relative score (0-100)
    "trend": 0.25,      # Moving average trend positioning (0-100)
    "volume": 0.15      # Recent volume vs 20-day baseline average (0-100)
}

def calculate_ticker_signals(raw_query: str) -> Optional[Dict[str, Any]]:
    resolved = resolve_ticker(raw_query)
    if not resolved:
        return None

    ticker = resolved.upper()
    summary = get_cached_summary(ticker)
    if not summary:
        return None

    news = get_cached_news(ticker)
    sentiment_data = predict_stock_sentiment(ticker, news)

    up_prob = sentiment_data.get("up_probability", 0.50)
    sentiment_score = round(up_prob * 100, 1)

    hist = get_price_history(ticker, period="6mo")
    
    momentum_score = 50.0
    trend_score = 50.0
    volume_score = 50.0
    
    rationale_parts = []

    if not hist.empty and len(hist) >= 20:
        closes = hist["Close"].values
        volumes = hist["Volume"].values
        
        latest_close = closes[-1]
        
        close_20d_ago = closes[-20] if len(closes) >= 20 else closes[0]
        ret_20d = ((latest_close - close_20d_ago) / close_20d_ago) * 100
        momentum_score = max(0.0, min(100.0, 50.0 + (ret_20d * 3.33)))
        
        if ret_20d > 2.0:
            rationale_parts.append(f"Positive 20-day momentum (+{ret_20d:.1f}%)")
        elif ret_20d < -2.0:
            rationale_parts.append(f"Negative 20-day momentum ({ret_20d:.1f}%)")
        else:
            rationale_parts.append("Flat 20-day momentum")

        ma50 = closes[-50:].mean() if len(closes) >= 50 else closes.mean()
        ma200 = closes[-200:].mean() if len(closes) >= 200 else closes.mean()
        
        above_50 = latest_close >= ma50
        above_200 = latest_close >= ma200
        
        if above_50 and above_200:
            trend_score = 90.0
            rationale_parts.append("Trading above 50-day and 200-day MAs")
        elif above_50:
            trend_score = 70.0
            rationale_parts.append("Trading above 50-day MA")
        elif above_200:
            trend_score = 40.0
            rationale_parts.append("Trading below 50-day MA but above 200-day MA")
        else:
            trend_score = 15.0
            rationale_parts.append("Trading below 50-day and 200-day MAs")

        avg_vol_5d = volumes[-5:].mean() if len(volumes) >= 5 else volumes.mean()
        avg_vol_20d = volumes[-20:].mean() if len(volumes) >= 20 else volumes.mean()
        vol_ratio = avg_vol_5d / avg_vol_20d if avg_vol_20d > 0 else 1.0
        
        volume_score = max(0.0, min(100.0, 50.0 + ((vol_ratio - 1.0) * 100)))
        if vol_ratio > 1.1:
            rationale_parts.append("Rising volume interest")
        elif vol_ratio < 0.9:
            rationale_parts.append("Decreasing volume")
        else:
            rationale_parts.append("Average volume levels")
    else:
        rationale_parts.append("Limited historical trading data")

    if sentiment_data["sentiment"] == "bullish":
        rationale_parts.insert(0, "Positive headline sentiment signal")
    elif sentiment_data["sentiment"] == "bearish":
        rationale_parts.insert(0, "Negative headline sentiment signal")
    else:
        rationale_parts.insert(0, "Neutral headline sentiment signal")

    composite_score = round(
        (sentiment_score * SCORE_WEIGHTS["sentiment"]) +
        (momentum_score * SCORE_WEIGHTS["momentum"]) +
        (trend_score * SCORE_WEIGHTS["trend"]) +
        (volume_score * SCORE_WEIGHTS["volume"]),
        1
    )

    rationale_text = "; ".join(rationale_parts)

    return {
        "ticker": ticker,
        "company_name": summary["company_name"],
        "current_price": summary["current_price"],
        "previous_close": summary["previous_close"],
        "change_pct": summary["change_pct"],
        "currency": summary.get("currency", "USD"),
        "currency_symbol": summary.get("currency_symbol", "$"),
        "composite_score": composite_score,
        "sentiment": sentiment_data["sentiment"],
        "components": {
            "sentiment": sentiment_score,
            "momentum": round(momentum_score, 1),
            "trend": round(trend_score, 1),
            "volume": round(volume_score, 1)
        },
        "rationale": rationale_text,
        "last_updated": summary.get("last_updated", datetime.utcnow().isoformat())
    }

def rank_watchlist_signals(tickers: List[str]) -> List[Dict[str, Any]]:
    results = []
    for raw_t in tickers:
        sig = calculate_ticker_signals(raw_t)
        if sig:
            results.append(sig)
    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return results
