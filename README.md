# Embeddable Stock Research Module & Periodical Charts (Self-Scraped, Self-Trained, No Cloud AI)

A lightweight, zero-paid-API stock research module engineered to be embedded inside desktop or mobile host applications (via Webview drawer or headless REST API).

---

## 🌟 Key Features

1. **Periodical Stock Charts Component**: Time-series visualizers (`1D`, `1W`, `1M`, `1Y`, `ALL`) formatted for `380px–420px` drawer panels.
2. **Zero Third-Party AI / LLM Costs**: Powered by a self-built **scikit-learn** model (`TfidfVectorizer` + `LogisticRegression` / `MultinomialNB` / `RandomForest`).
3. **Intelligent Ticker Resolution**: Resolves company names and free text (`"sbi stock"`, `"reliance"`, `"apple shares"`) to exchange symbols using Yahoo search-suggest API and suffix fallbacks (`.NS`, `.BO`, `.L`).
4. **Non-Directive Signal Screener**: Transparent composite score engine (0–100) combining Sentiment (35%), Momentum (25%), Trend (25%), and Volume (15%). Strictly signal rankings, NOT investment advice.
5. **Unified StockCard Component**: Reusable, scan-at-a-glance display unit.
6. **Embeddable Webview Panel**: Renders chromeless fixed-width drawer UI (`380px–420px`) with dynamic theme switching and `window.postMessage` host lifecycle events.
7. **Headless REST API**: 7 documented JSON endpoints for native UI host integration.

---

## 🚀 Quickstart Guide

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## 🤖 Data Collection & Model Training

Run the offline scripts to build your training dataset and generate `backend/ml/model.joblib`:

```bash
python backend/ml/collect_data.py --tickers AAPL MSFT GOOGL NVDA TSLA --days 60
python backend/ml/train_model.py
```

---

## 💻 Running the Application Server

Launch FastAPI with Uvicorn:
```bash
uvicorn backend.main:app --reload --port 8000
```

- **Embedded Webview Drawer UI**: [http://localhost:8000/?mode=embedded&theme=dark](http://localhost:8000/?mode=embedded&theme=dark)
- **Periodical Chart REST API**: [http://localhost:8000/api/stock/AAPL/chart?period=1M](http://localhost:8000/api/stock/AAPL/chart?period=1M)
- **Signal Screener API**: [http://localhost:8000/api/screener/rank?tickers=AAPL,MSFT,NVDA,SBIN.NS](http://localhost:8000/api/screener/rank?tickers=AAPL,MSFT,NVDA,SBIN.NS)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
# StockAi
