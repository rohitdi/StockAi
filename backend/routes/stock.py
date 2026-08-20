from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import verify_token
from backend.cache import get_cached_summary, get_cached_news, get_cached_chart
from backend.ml.infer import predict_stock_sentiment
from backend.scraping.ticker_resolver import resolve_ticker

router = APIRouter(prefix="/api/stock", tags=["Stock Data"])

@router.get("/{ticker}/summary")
def get_stock_summary_api(ticker: str, auth_user: Dict[str, Any] = Depends(verify_token)):
    """
    Returns real-time price & fundamentals summary for the host app.
    Supports raw free-text queries, company names (e.g. "sbi stock", "reliance") and tickers.
    """
    resolved = resolve_ticker(ticker)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"Couldn't identify a matching stock for '{ticker}' — try using the full exchange ticker symbol (e.g. SBIN.NS or AAPL)."
        )

    summary = get_cached_summary(resolved)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"Couldn't identify a matching stock for '{ticker}' (resolved symbol '{resolved}') — verify the ticker symbol is valid."
        )
    return summary

@router.get("/{ticker}/chart")
def get_stock_chart_api(
    ticker: str,
    period: str = Query("1M", description="Chart timeframe: 1D, 1W, 1M, 1Y, 5Y, ALL"),
    auth_user: Dict[str, Any] = Depends(verify_token)
):
    """
    Returns structured historical time-series price data formatted for frontend line chart visualizers.
    Timeframes supported: 1D, 1W, 1M, 1Y, 5Y, ALL.
    """
    resolved = resolve_ticker(ticker)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"Couldn't identify a matching stock for '{ticker}' — try using the full exchange ticker symbol (e.g. SBIN.NS or AAPL)."
        )

    chart_data = get_cached_chart(resolved, period=period)
    if not chart_data:
        raise HTTPException(
            status_code=404,
            detail=f"Time-series chart data for symbol '{resolved}' (period={period}) could not be retrieved."
        )
    return chart_data

@router.get("/{ticker}/news")
def get_stock_news_api(ticker: str, auth_user: Dict[str, Any] = Depends(verify_token)):
    """
    Returns scraped Google News headlines (cached).
    """
    resolved = resolve_ticker(ticker) or ticker.upper()
    news = get_cached_news(resolved)
    return {
        "query": ticker,
        "ticker": resolved.upper(),
        "count": len(news),
        "headlines": news
    }

@router.get("/{ticker}/sentiment")
def get_stock_sentiment_api(ticker: str, auth_user: Dict[str, Any] = Depends(verify_token)):
    """
    Returns self-trained scikit-learn model sentiment lean, confidence score, and honesty disclaimer.
    """
    resolved = resolve_ticker(ticker) or ticker.upper()
    news = get_cached_news(resolved)
    sentiment_result = predict_stock_sentiment(resolved, news)
    return sentiment_result
