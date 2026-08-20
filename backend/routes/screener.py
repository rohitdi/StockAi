from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from backend.auth import verify_token
from backend.screener import rank_watchlist_signals

router = APIRouter(prefix="/api/screener", tags=["Signal Screener"])

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "SBIN.NS", "RELIANCE.NS"]

@router.get("/rank")
def get_screener_rankings(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker list e.g. AAPL,MSFT,NVDA,SBIN.NS"),
    auth_user: Dict[str, Any] = Depends(verify_token)
):
    """
    Ranks a watchlist of tickers by a transparent composite score (0-100) derived from 
    headline sentiment, momentum, trend, and volume. 
    Strictly a ranking of statistical signals — NOT investment recommendations.
    """
    if tickers and tickers.strip():
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    else:
        ticker_list = DEFAULT_WATCHLIST

    if not ticker_list:
        raise HTTPException(status_code=400, detail="No valid ticker symbols provided.")

    ranked_results = rank_watchlist_signals(ticker_list)
    
    return {
        "count": len(ranked_results),
        "disclaimer": (
            "Signal rankings reflect relative statistical indicator scores only. "
            "This is an analytical tool for portfolio/educational demonstration, NOT financial or investment advice."
        ),
        "rankings": ranked_results
    }
