from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.db.database import db_client
from backend.scraping.prices import get_stock_summary

router = APIRouter(prefix="/api/alerts", tags=["Price Alerts"])

class CreateAlertRequest(BaseModel):
    ticker: str
    target_price: float
    condition: str = "above"  # "above" | "below"
    currency_symbol: Optional[str] = "$"
    user_id: Optional[str] = "guest"

@router.post("")
def create_price_alert(req: CreateAlertRequest) -> Dict[str, Any]:
    """
    Creates a new stock price threshold alert.
    """
    if req.target_price <= 0:
        raise HTTPException(status_code=400, detail="Target price must be greater than 0")
    
    clean_ticker = req.ticker.strip().upper()
    alert = db_client.create_alert(
        ticker=clean_ticker,
        target_price=req.target_price,
        condition=req.condition,
        currency_symbol=req.currency_symbol or "$",
        user_id=req.user_id or "guest"
    )
    return {
        "status": "success",
        "message": f"Alert set for {clean_ticker} when price goes {req.condition} {req.currency_symbol}{req.target_price}",
        "alert": alert
    }

@router.get("")
def list_active_alerts(user_id: Optional[str] = None, status: str = "active") -> Dict[str, Any]:
    """
    Lists active or historical price alerts.
    """
    alerts = db_client.get_alerts(status=status, user_id=user_id)
    return {
        "count": len(alerts),
        "alerts": alerts
    }

@router.post("/check")
def check_price_alerts(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates all active alerts against latest real-time prices.
    Returns any alerts triggered during this check.
    """
    active_alerts = db_client.get_alerts(status="active", user_id=user_id)
    triggered = []

    # Cache summaries across same tickers in check batch
    summaries = {}
    for a in active_alerts:
        ticker = a["ticker"]
        if ticker not in summaries:
            summaries[ticker] = get_stock_summary(ticker)
        
        summary = summaries[ticker]
        if not summary:
            continue
        
        curr_price = float(summary.get("current_price", 0))
        target_price = float(a["target_price"])
        cond = a["condition"].lower()

        is_hit = False
        if "above" in cond and curr_price >= target_price:
            is_hit = True
        elif "below" in cond and curr_price <= target_price:
            is_hit = True

        if is_hit:
            db_client.trigger_alert(a["id"])
            triggered.append({
                "alert_id": a["id"],
                "ticker": ticker,
                "target_price": target_price,
                "current_price": curr_price,
                "condition": cond,
                "currency_symbol": a.get("currency_symbol", "$"),
                "message": f"🚨 {ticker} has hit {a.get('currency_symbol', '$')}{curr_price:.2f} (Target: {cond} {a.get('currency_symbol', '$')}{target_price:.2f})!"
            })

    return {
        "checked_count": len(active_alerts),
        "triggered_count": len(triggered),
        "triggered_alerts": triggered
    }

@router.delete("/{alert_id}")
def remove_price_alert(alert_id: str) -> Dict[str, Any]:
    """
    Deletes an alert by ID.
    """
    success = db_client.delete_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "message": "Alert deleted"}
