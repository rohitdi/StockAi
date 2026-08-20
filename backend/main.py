import os
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import markdown

from backend.routes.health import router as health_router
from backend.routes.stock import router as stock_router
from backend.routes.query import router as query_router, process_qa_query, QueryRequest
from backend.routes.screener import router as screener_router, DEFAULT_WATCHLIST
from backend.routes.alerts import router as alerts_router
from backend.cache import get_cached_summary, get_cached_news, get_cached_chart
from backend.ml.infer import predict_stock_sentiment
from backend.screener import rank_watchlist_signals

app = FastAPI(
    title="Embeddable Stock Research Module",
    description="Zero-paid-API self-hosted stock research, scikit-learn sentiment ML, and rule-based Q&A module.",
    version="1.0.0"
)

# CORS Configuration for Host App Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files & Templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "frontend", "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount REST API Routers
app.include_router(health_router)
app.include_router(stock_router)
app.include_router(query_router)
app.include_router(screener_router)
app.include_router(alerts_router)

@app.get("/", response_class=HTMLResponse)
def get_panel_view(
    request: Request,
    mode: str = Query("standalone"),  # "embedded" or "standalone"
    theme: str = Query("dark"),       # "dark" or "light"
    token: str = Query(""),           # host JWT token
    ticker: str = Query("AAPL")       # default ticker
):
    from backend.scraping.ticker_resolver import resolve_ticker
    resolved = resolve_ticker(ticker) or ticker.upper()
    summary = get_cached_summary(resolved)
    news = get_cached_news(resolved) if summary else []
    sentiment = predict_stock_sentiment(resolved, news) if summary else None
    chart = get_cached_chart(resolved, period="1M") if summary else None

    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "mode": mode,
            "theme": theme,
            "token": token,
            "raw_ticker": ticker,
            "ticker": resolved.upper(),
            "summary": summary,
            "news": news,
            "sentiment": sentiment,
            "chart": chart
        }
    )

@app.post("/partials/summary", response_class=HTMLResponse)
def get_summary_partial(
    request: Request,
    ticker: str = Form(...)
):
    from backend.scraping.ticker_resolver import resolve_ticker
    raw_query = ticker.strip()
    resolved = resolve_ticker(raw_query)
    
    summary = get_cached_summary(resolved) if resolved else None
    news = get_cached_news(resolved) if summary else []
    sentiment = predict_stock_sentiment(resolved, news) if summary else None
    chart = get_cached_chart(resolved, period="1M") if summary else None

    return templates.TemplateResponse(
        "partials/summary.html",
        {
            "request": request,
            "raw_ticker": raw_query,
            "ticker": resolved.upper() if resolved else raw_query.upper(),
            "summary": summary,
            "news": news,
            "sentiment": sentiment,
            "chart": chart
        }
    )

@app.post("/partials/chart", response_class=HTMLResponse)
def get_chart_partial(
    request: Request,
    ticker: str = Form(...),
    period: str = Form("1M")
):
    from backend.scraping.ticker_resolver import resolve_ticker
    resolved = resolve_ticker(ticker) or ticker.upper()
    chart = get_cached_chart(resolved, period=period)
    summary = get_cached_summary(resolved)

    return templates.TemplateResponse(
        "partials/stock_chart.html",
        {
            "request": request,
            "chart": chart,
            "summary": summary
        }
    )

@app.post("/partials/detailed_chart", response_class=HTMLResponse)
def get_detailed_chart_partial(
    request: Request,
    ticker: str = Form(...),
    period: str = Form("1Y")
):
    from backend.scraping.ticker_resolver import resolve_ticker
    resolved = resolve_ticker(ticker) or ticker.upper()
    chart = get_cached_chart(resolved, period=period)
    summary = get_cached_summary(resolved)

    return templates.TemplateResponse(
        "partials/detailed_chart_modal.html",
        {
            "request": request,
            "chart": chart,
            "summary": summary,
            "ticker": resolved.upper()
        }
    )

@app.post("/partials/qa_response", response_class=HTMLResponse)
def get_qa_partial(
    request: Request,
    question: str = Form(...),
    ticker: str = Form("")
):
    req = QueryRequest(question=question, ticker=ticker)
    res = process_qa_query(req, auth_user={"sub": "ui-user"})
    answer_html = markdown.markdown(res.get("answer", ""))
    
    return templates.TemplateResponse(
        "partials/qa_response.html",
        {
            "request": request,
            "question": question,
            "response": res,
            "answer_html": answer_html
        }
    )

@app.post("/partials/screener", response_class=HTMLResponse)
def get_screener_partial(
    request: Request,
    tickers: str = Form("")
):
    if tickers and tickers.strip():
        t_list = [t.strip() for t in tickers.split(",") if t.strip()]
    else:
        t_list = DEFAULT_WATCHLIST

    rankings = rank_watchlist_signals(t_list)

    return templates.TemplateResponse(
        "partials/screener.html",
        {
            "request": request,
            "rankings": rankings
        }
    )
