import re
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth import verify_token
from backend.cache import get_cached_summary, get_cached_news
from backend.ml.infer import predict_stock_sentiment
from backend.scraping.ticker_resolver import resolve_ticker, clean_query

router = APIRouter(prefix="/api", tags=["Q&A Query"])

class QueryRequest(BaseModel):
    question: str
    ticker: Optional[str] = None

def extract_target_from_question(question: str, intent_type: str) -> Optional[str]:
    """
    Extracts raw ticker/entity query string from natural language question patterns.
    """
    q_lower = question.lower().strip()
    
    if intent_type == "price":
        # 1. Matches: "price of sbi", "price for AAPL", "quote for reliance", "what is TSLA trading at", "how much is sbi stock"
        m1 = re.search(r"(?:price\s+of|price\s+for|price\s+on|quote\s+for|quote\s+of|what\s+is|how\s+much\s+is)\s+(.+?)(?:\s+trading\s+at|\s+worth|\s+cost|\?|$)", q_lower)
        if m1 and m1.group(1).strip():
            return m1.group(1).strip()

        # 2. Matches: "sbi price", "reliance quote", "AAPL trading at"
        m2 = re.search(r"(.+?)\s+(?:price|quote|trading\s+at|worth|cost)", q_lower)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()

    elif intent_type == "news":
        # 1. Matches: "news on sbi", "latest headlines for reliance", "news about AAPL"
        m1 = re.search(r"(?:news\s+on|news\s+about|news\s+for|headlines\s+for|latest\s+on|latest\s+for)\s+(.+?)(?:\?|$)", q_lower)
        if m1 and m1.group(1).strip():
            return m1.group(1).strip()

        # 2. Matches: "sbi news", "reliance headlines", "NVDA updates"
        m2 = re.search(r"(.+?)\s+(?:news|headlines|latest|updates|articles)", q_lower)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()

    elif intent_type == "sentiment":
        # 1. Matches: "sentiment for sbi", "sentiment on reliance", "is AAPL bullish", "prediction for TSLA"
        m1 = re.search(r"(?:sentiment\s+for|sentiment\s+on|sentiment\s+about|predict\s+for|prediction\s+for|is)\s+(.+?)(?:\s+bullish|\s+bearish|\?|$)", q_lower)
        if m1 and m1.group(1).strip():
            return m1.group(1).strip()

        # 2. Matches: "sbi sentiment", "reliance prediction", "NVDA model"
        m2 = re.search(r"(.+?)\s+(?:sentiment|prediction|lean|model|forecast)", q_lower)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()

    return None

@router.post("/query")
def process_qa_query(body: QueryRequest, auth_user: Dict[str, Any] = Depends(verify_token)):
    question = body.question.strip()
    q_lower = question.lower()
    
    # Determine Intent Type
    is_price = any(k in q_lower for k in ["price", "quote", "trading at", "worth", "cost"])
    is_news = any(k in q_lower for k in ["news", "headline", "latest", "article", "update"])
    is_sentiment = any(k in q_lower for k in ["sentiment", "bullish", "bearish", "predict", "lean", "model", "forecast"])

    # 1. Price Intent
    if is_price:
        raw_target = extract_target_from_question(question, "price")
        # Fallback to question itself or body.ticker if regex extraction is blank
        if not raw_target:
            raw_target = question
            
        resolved_ticker = resolve_ticker(raw_target)
        
        if not resolved_ticker:
            return {
                "intent": "price",
                "success": False,
                "ticker": None,
                "answer": f"Couldn't identify a matching stock for '{question}' — try using the full exchange ticker symbol (e.g. SBIN.NS or AAPL).",
                "matched_pattern": "price_lookup"
            }
            
        summary = get_cached_summary(resolved_ticker)
        if not summary:
            return {
                "intent": "price",
                "success": False,
                "ticker": resolved_ticker,
                "answer": f"Unable to fetch price data for symbol '{resolved_ticker}'. Please verify the ticker symbol is valid.",
                "matched_pattern": "price_lookup"
            }
            
        sign = "+" if summary['change_pct'] >= 0 else ""
        answer = (
            f"**{summary['company_name']} ({summary['ticker']})** is currently trading at **${summary['current_price']}** "
            f"({sign}{summary['change_pct']}% today).\n\n"
            f"• **Previous Close:** ${summary['previous_close']}\n"
            f"• **Volume:** {summary['volume']:,}\n"
            f"• **52-Week Range:** ${summary['fifty_two_low']} - ${summary['fifty_two_high']}"
        )
        return {
            "intent": "price",
            "success": True,
            "ticker": summary['ticker'],
            "answer": answer,
            "data": summary,
            "matched_pattern": "price_lookup"
        }

    # 2. News Intent
    elif is_news:
        raw_target = extract_target_from_question(question, "news") or question
        resolved_ticker = resolve_ticker(raw_target)

        if not resolved_ticker:
            return {
                "intent": "news",
                "success": False,
                "ticker": None,
                "answer": f"Couldn't identify a matching stock for '{question}' — try using the full exchange ticker symbol (e.g. SBIN.NS or AAPL).",
                "matched_pattern": "news_lookup"
            }
            
        news = get_cached_news(resolved_ticker)
        if not news:
            return {
                "intent": "news",
                "success": False,
                "ticker": resolved_ticker,
                "answer": f"No recent headlines found for ticker '{resolved_ticker}'.",
                "matched_pattern": "news_lookup"
            }
            
        news_items = news[:5]
        bullets = "\n".join([f"• [{item['title']}]({item['link']}) *({item['source']})*" for item in news_items])
        answer = f"### Recent Headlines for **{resolved_ticker}**\n\n{bullets}"
        return {
            "intent": "news",
            "success": True,
            "ticker": resolved_ticker,
            "answer": answer,
            "data": news_items,
            "matched_pattern": "news_lookup"
        }

    # 3. Sentiment Intent
    elif is_sentiment:
        raw_target = extract_target_from_question(question, "sentiment") or question
        resolved_ticker = resolve_ticker(raw_target)

        if not resolved_ticker:
            return {
                "intent": "sentiment",
                "success": False,
                "ticker": None,
                "answer": f"Couldn't identify a matching stock for '{question}' — try using the full exchange ticker symbol (e.g. SBIN.NS or AAPL).",
                "matched_pattern": "sentiment_lookup"
            }
            
        news = get_cached_news(resolved_ticker)
        sentiment_res = predict_stock_sentiment(resolved_ticker, news)
        
        badge = "🟢 BULLISH" if sentiment_res['sentiment'] == "bullish" else "🔴 BEARISH" if sentiment_res['sentiment'] == "bearish" else "⚪ NEUTRAL"
        answer = (
            f"### Self-Trained AI Model Signal for **{resolved_ticker}**\n\n"
            f"**Model Signal:** {badge}\n"
            f"**Confidence Score:** {int(sentiment_res['confidence'] * 100)}%\n"
            f"**Analysis:** {sentiment_res['summary_text']} based on {sentiment_res['headline_count']} recent headlines.\n\n"
            f"*> Note: {sentiment_res['disclaimer']}*"
        )
        return {
            "intent": "sentiment",
            "success": True,
            "ticker": resolved_ticker,
            "answer": answer,
            "data": sentiment_res,
            "matched_pattern": "sentiment_lookup"
        }

    # 4. Help / Fallback Intent
    else:
        resolved_ticker = resolve_ticker(question)
        answer = (
            "### Rule-Based Intent Matcher\n"
            "This assistant uses keyword pattern matching (not a free-form LLM chatbot).\n\n"
            "**Supported Question Formats:**\n"
            "1. **Price Quote:** `price of sbi`, `sbi price`, `what is reliance trading at`\n"
            "2. **Stock News:** `news on MSFT`, `latest headlines for NVDA`\n"
            "3. **Model Sentiment:** `sentiment for AMZN`, `is META bullish?`\n\n"
            "**Examples:** SBIN.NS (SBI), RELIANCE.NS, AAPL, TSLA"
        )
        return {
            "intent": "help",
            "success": True,
            "ticker": resolved_ticker,
            "answer": answer,
            "matched_pattern": "pattern_help"
        }
