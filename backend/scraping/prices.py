import yfinance as yf
from typing import Dict, Any, Optional, List
import pandas as pd

def get_stock_summary(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetches real-time price & fundamentals summary for a ticker via yfinance.
    """
    clean_ticker = ticker.strip().upper()
    try:
        t = yf.Ticker(clean_ticker)
        # Fast history check
        hist = t.history(period="5d")
        if hist.empty:
            return None

        latest_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else latest_close
        pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
        volume = int(hist["Volume"].iloc[-1])

        # Attempt to load info safely
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass

        company_name = info.get("shortName") or info.get("longName") or clean_ticker
        market_cap = info.get("marketCap") or 0
        pe_ratio = info.get("trailingPE") or info.get("forwardPE") or 0
        fifty_two_high = info.get("fiftyTwoWeekHigh") or float(hist["High"].max())
        fifty_two_low = info.get("fiftyTwoWeekLow") or float(hist["Low"].min())
        currency = info.get("currency", "USD")

        return {
            "ticker": clean_ticker,
            "company_name": company_name,
            "current_price": round(latest_close, 2),
            "previous_close": round(prev_close, 2),
            "change_pct": pct_change,
            "volume": volume,
            "market_cap": market_cap,
            "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
            "fifty_two_high": round(fifty_two_high, 2),
            "fifty_two_low": round(fifty_two_low, 2),
            "currency": currency,
            "last_updated": pd.Timestamp.now().isoformat()
        }
    except Exception as e:
        print(f"[Price Engine] Error fetching data for {ticker}: {e}")
        return None

def get_price_history(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """
    Fetches historical OHLCV data for dataset labeling and technical signals.
    """
    clean_ticker = ticker.strip().upper()
    try:
        t = yf.Ticker(clean_ticker)
        return t.history(period=period)
    except Exception as e:
        print(f"[Price Engine] Error fetching price history for {ticker}: {e}")
        return pd.DataFrame()

# Timeframe Period Mapper
PERIOD_MAP = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "15m"),
    "1M": ("1mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
    "ALL": ("5y", "1wk")
}

def get_stock_chart_data(ticker: str, period: str = "1M") -> Optional[Dict[str, Any]]:
    """
    Fetches structured time-series historical price data for charting.
    Periods supported: 1D, 1W, 1M, 1Y, 5Y, ALL.
    """
    clean_ticker = ticker.strip().upper()
    period_clean = period.upper() if period else "1M"
    if period_clean not in PERIOD_MAP:
        period_clean = "1M"

    yf_period, interval = PERIOD_MAP[period_clean]

    try:
        t = yf.Ticker(clean_ticker)
        hist = t.history(period=yf_period, interval=interval)
        
        if hist.empty:
            # Retry with daily interval if intraday failed
            hist = t.history(period=yf_period, interval="1d")

        if hist.empty:
            return None

        # Clean timestamps formatting
        timestamps = []
        for idx in hist.index:
            if hasattr(idx, "strftime"):
                if period_clean in ["1D", "1W"]:
                    timestamps.append(idx.strftime("%b %d %H:%M"))
                else:
                    timestamps.append(idx.strftime("%Y-%m-%d"))
            else:
                timestamps.append(str(idx)[:10])

        prices = [round(float(p), 2) for p in hist["Close"].values]
        volumes = [int(v) for v in hist["Volume"].values]

        if not prices:
            return None

        start_price = prices[0]
        end_price = prices[-1]
        change_abs = round(end_price - start_price, 2)
        change_pct = round(((end_price - start_price) / start_price) * 100, 2) if start_price > 0 else 0.0
        trend = "up" if change_pct >= 0 else "down"

        high_price = round(float(hist["High"].max()), 2)
        low_price = round(float(hist["Low"].min()), 2)

        return {
            "ticker": clean_ticker,
            "period": period_clean,
            "data_points": len(prices),
            "start_price": start_price,
            "end_price": end_price,
            "change_abs": change_abs,
            "change_pct": change_pct,
            "trend": trend,
            "high": high_price,
            "low": low_price,
            "timestamps": timestamps,
            "prices": prices,
            "volumes": volumes,
            "last_updated": pd.Timestamp.now().isoformat()
        }
    except Exception as e:
        print(f"[Price Engine] Error fetching chart data for {ticker} (period={period_clean}): {e}")
        return None
