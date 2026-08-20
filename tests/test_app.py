import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.scraping.prices import get_stock_summary, get_stock_chart_data

client = TestClient(app)

def test_currency_symbol_and_price_resilience():
    print("\n--- Testing Currency Symbol Mapping & Price Drop-NaN Resilience ---")
    
    # Test 1: Indian Stock SBIN.NS (should return ₹ currency symbol and valid close price)
    summary_sbi = get_stock_summary("SBIN.NS")
    assert summary_sbi is not None
    assert summary_sbi["currency"] == "INR"
    assert summary_sbi["currency_symbol"] == "₹"
    assert summary_sbi["current_price"] > 0
    print(f"✓ SBIN.NS returned currency: {summary_sbi['currency']} ({summary_sbi['currency_symbol']}), Price: {summary_sbi['current_price']}")

    # Test 2: US Stock AAPL (should return $ currency symbol)
    summary_aapl = get_stock_summary("AAPL")
    assert summary_aapl is not None
    assert summary_aapl["currency"] == "USD"
    assert summary_aapl["currency_symbol"] == "$"
    print(f"✓ AAPL returned currency: {summary_aapl['currency']} ({summary_aapl['currency_symbol']}), Price: {summary_aapl['current_price']}")

def test_partials_rendering():
    print("\n--- Testing Partials Currency & Detailed Chart Rendering ---")
    
    # Test POST /partials/summary for SBIN.NS
    r1 = client.post("/partials/summary", data={"ticker": "SBIN.NS"})
    assert r1.status_code == 200
    assert "₹" in r1.text
    assert ",nan" not in r1.text.lower()
    assert "nan," not in r1.text.lower()
    print("✓ Summary partial view returned correct Rupee symbol (₹) and no NaN coordinates!")

    # Test POST /partials/chart for SBIN.NS
    r2 = client.post("/partials/chart", data={"ticker": "SBIN.NS", "period": "1M"})
    assert r2.status_code == 200
    assert "₹" in r2.text
    assert ",nan" not in r2.text.lower()
    assert "nan," not in r2.text.lower()
    print("✓ Chart partial view returned correct Rupee symbol (₹) and no NaN coordinates!")

    # Test POST /partials/detailed_chart for SBIN.NS
    r3 = client.post("/partials/detailed_chart", data={"ticker": "SBIN.NS", "period": "1Y"})
    assert r3.status_code == 200
    assert "detailed-chart-modal" in r3.text
    assert "50 DMA" in r3.text
    assert "200 DMA" in r3.text
    assert "financialChartCanvas" in r3.text
    print("✓ Sleek Area Chart Modal returned successfully with canvas, 50 DMA, and 200 DMA controls!")

def test_price_alerts_api():
    print("\n--- Testing Price Alerts API & Background Evaluation ---")
    
    # 1. Create alert: Above 500 for SBIN.NS (which is currently > 1000, so it will trigger immediately on check)
    r_create = client.post("/api/alerts", json={
        "ticker": "SBIN.NS",
        "target_price": 500.0,
        "condition": "above",
        "currency_symbol": "₹"
    })
    assert r_create.status_code == 200
    data = r_create.json()
    assert data["status"] == "success"
    alert_id = data["alert"]["id"]
    print("✓ Created price alert with ID:", alert_id)

    # 2. List alerts
    r_list = client.get("/api/alerts")
    assert r_list.status_code == 200
    assert r_list.json()["count"] >= 1
    print(f"✓ Listed {r_list.json()['count']} active alerts")

    # 3. Check alerts
    r_check = client.post("/api/alerts/check")
    assert r_check.status_code == 200
    check_data = r_check.json()
    assert check_data["triggered_count"] >= 1
    triggered = [a for a in check_data["triggered_alerts"] if a["alert_id"] == alert_id]
    assert len(triggered) == 1
    print(f"✓ Alert triggered successfully: {triggered[0]['message']}")

    # 4. Clean up alert
    r_del = client.delete(f"/api/alerts/{alert_id}")
    assert r_del.status_code == 200
    print("✓ Deleted test alert")

def test_ohlc_data_integrity():
    print("\n--- Testing OHLC Candlestick & Bar Data Integrity ---")
    chart_data = get_stock_chart_data("AAPL", period="1mo")
    assert chart_data is not None
    assert "opens" in chart_data and len(chart_data["opens"]) > 0
    assert "highs" in chart_data and len(chart_data["highs"]) > 0
    assert "lows" in chart_data and len(chart_data["lows"]) > 0
    assert "closes" in chart_data and len(chart_data["closes"]) > 0
    assert "ohlc" in chart_data and len(chart_data["ohlc"]) > 0

    # Ensure high >= max(open, close) and low <= min(open, close)
    for candle in chart_data["ohlc"]:
        assert candle["high"] >= max(candle["open"], candle["close"])
        assert candle["low"] <= min(candle["open"], candle["close"])
        assert candle["high"] > candle["low"] # non-flat candles

    print(f"✓ Validated {len(chart_data['ohlc'])} OHLC candles with non-flat upper/lower wicks!")

if __name__ == "__main__":
    test_currency_symbol_and_price_resilience()
    test_partials_rendering()
    test_ohlc_data_integrity()
    test_price_alerts_api()
    print("\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
