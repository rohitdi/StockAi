import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.scraping.ticker_resolver import resolve_ticker
from backend.screener import rank_watchlist_signals

client = TestClient(app)

def test_stock_chart_api():
    print("\n--- Testing Periodical Stock Charts Engine & API ---")
    
    # Test 1: GET /api/stock/AAPL/chart?period=1M
    response = client.get("/api/stock/AAPL/chart?period=1M")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["period"] == "1M"
    assert "prices" in data
    assert len(data["prices"]) > 0
    assert "timestamps" in data
    assert "trend" in data
    print(f"✓ Chart API test (1M) passed! Datapoints: {data['data_points']}, Trend: {data['trend']} ({data['change_pct']}%)")

    # Test 2: Chart with Non-US stock free text query "sbi stock" (period=1W)
    res_non_us = client.get("/api/stock/sbi stock/chart?period=1W")
    assert res_non_us.status_code == 200
    d_non_us = res_non_us.json()
    assert d_non_us["ticker"] == "SBIN.NS"
    print(f"✓ Non-US Stock Chart API test ('sbi stock' -> SBIN.NS) passed!")

    # Test 3: Chart HTMX partial view POST /partials/chart
    res_partial = client.post("/partials/chart", data={"ticker": "AAPL", "period": "1Y"})
    assert res_partial.status_code == 200
    assert "chart-card" in res_partial.text
    assert "1Y" in res_partial.text
    print("✓ Chart HTMX partial view test passed!")

def test_screener_engine_and_api():
    print("\n--- Testing Section 2.6 Signal Screener Engine & API ---")
    tickers = ["AAPL", "MSFT", "SBIN.NS"]
    rankings = rank_watchlist_signals(tickers)
    assert len(rankings) > 0
    assert "composite_score" in rankings[0]
    
    response = client.get("/api/screener/rank?tickers=AAPL,MSFT,NVDA")
    assert response.status_code == 200
    data = response.json()
    assert "rankings" in data
    print("✓ Screener REST API endpoint GET /api/screener/rank passed!")

def test_ticker_resolver():
    print("\n--- Testing Section 2.5 Ticker Resolution Pipeline ---")
    res1 = resolve_ticker("sbi stock")
    assert res1 == "SBIN.NS"
    res2 = resolve_ticker("reliance")
    assert res2 == "RELIANCE.NS"
    res3 = resolve_ticker("apple shares")
    assert res3 == "AAPL"
    print("✓ Ticker resolver tests passed!")

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✓ Health check endpoint test passed!")

def test_embedded_panel_page():
    response = client.get("/?mode=embedded&theme=dark&ticker=AAPL")
    assert response.status_code == 200
    assert "Stock Intelligence" in response.text
    assert "mode-embedded" in response.text
    print("✓ Embedded webview panel drawer page test passed!")

def test_stock_summary_api():
    response = client.get("/api/stock/AAPL/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    print(f"✓ Stock summary API test passed! Price: ${data['current_price']}")

def test_stock_news_api():
    response = client.get("/api/stock/AAPL/news")
    assert response.status_code == 200
    print(f"✓ Stock news API test passed!")

def test_stock_sentiment_api():
    response = client.get("/api/stock/AAPL/sentiment")
    assert response.status_code == 200
    print(f"✓ Stock sentiment ML model API test passed!")

def test_intent_matcher_api():
    r1 = client.post("/api/query", json={"question": "price of sbi stock"})
    assert r1.status_code == 200
    assert r1.json()["intent"] == "price"
    print("✓ Rule-based Q&A Intent Matcher tests passed!")

if __name__ == "__main__":
    test_stock_chart_api()
    test_screener_engine_and_api()
    test_ticker_resolver()
    test_health_check()
    test_embedded_panel_page()
    test_stock_summary_api()
    test_stock_news_api()
    test_stock_sentiment_api()
    test_intent_matcher_api()
    print("\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
