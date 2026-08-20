import time
import random
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def fetch_google_html_fallback(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    clean_ticker = ticker.strip().upper()
    query = urllib.parse.quote(f"{clean_ticker} stock news")
    url = f"https://www.google.com/search?q={query}&tbm=nws"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200 or "sorry/index" in response.url:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        headlines = []
        articles = soup.find_all("div", class_=["n0fdjd", "So3B7b", "MjjYud", "WlyW2b"]) or soup.find_all("g-card")
        
        for art in articles[:limit]:
            title_tag = art.find(["div", "h3"], class_=["mCBkyc", "n0fdjd", "JheGif"]) or art.find("a")
            link_tag = art.find("a", href=True)
            
            if title_tag and link_tag:
                title = title_tag.get_text().strip()
                link = link_tag["href"]
                if link.startswith("/url?q="):
                    link = link.split("/url?q=")[1].split("&")[0]
                    
                headlines.append({
                    "ticker": clean_ticker,
                    "title": title,
                    "link": link,
                    "published_at": "Recent",
                    "source": "Google HTML Search (Best Effort)",
                    "scraper": "html_fallback"
                })

        return headlines
    except Exception as e:
        return []
