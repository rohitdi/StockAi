import os
import json
import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class DatabaseClient:
    def __init__(self):
        self.use_supabase = False
        self.supabase = None
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "stock_module.db")
        
        if SUPABASE_URL and SUPABASE_KEY and "your-supabase" not in SUPABASE_URL:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                self.use_supabase = True
                print("[DB] Initialized Supabase client successfully.")
            except Exception as e:
                print(f"[DB] Supabase init failed: {e}. Falling back to SQLite.")
                self._init_sqlite()
        else:
            print("[DB] No Supabase credentials set. Using local SQLite database.")
            self._init_sqlite()

    def _init_sqlite(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_cache_lookup ON search_cache (ticker, source, fetched_at);

            CREATE TABLE IF NOT EXISTS training_data (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                headline TEXT NOT NULL,
                headline_date TEXT NOT NULL,
                price_up_next_day INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                host_user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ticker_resolution_cache (
                id TEXT PRIMARY KEY,
                raw_query TEXT UNIQUE NOT NULL,
                resolved_ticker TEXT NOT NULL,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS price_alerts (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                target_price REAL NOT NULL,
                condition TEXT NOT NULL,
                currency_symbol TEXT DEFAULT '$',
                status TEXT DEFAULT 'active',
                user_id TEXT DEFAULT 'guest',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def get_cache(self, ticker: str, source: str, ttl_minutes: int = 30) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        if self.use_supabase:
            try:
                res = self.supabase.table("search_cache") \
                    .select("*") \
                    .eq("ticker", ticker) \
                    .eq("source", source) \
                    .order("fetched_at", desc=True) \
                    .limit(1) \
                    .execute()
                if res.data:
                    item = res.data[0]
                    fetched_at = datetime.fromisoformat(item["fetched_at"].replace("Z", "+00:00"))
                    now = datetime.now(fetched_at.tzinfo)
                    if (now - fetched_at).total_seconds() / 60 <= ttl_minutes:
                        return item["payload"]
            except Exception as e:
                print(f"[DB] Supabase cache fetch error: {e}")
        
        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload, fetched_at FROM search_cache WHERE ticker=? AND source=? ORDER BY fetched_at DESC LIMIT 1",
                (ticker, source)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                fetched_at = datetime.fromisoformat(row["fetched_at"])
                if (datetime.utcnow() - fetched_at).total_seconds() / 60 <= ttl_minutes:
                    return json.loads(row["payload"])
        except Exception as e:
            print(f"[DB] SQLite cache fetch error: {e}")

        return None

    def save_cache(self, ticker: str, source: str, payload: Dict[str, Any]):
        ticker = ticker.upper()
        import uuid
        cache_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()

        if self.use_supabase:
            try:
                self.supabase.table("search_cache").insert({
                    "ticker": ticker,
                    "source": source,
                    "payload": payload,
                    "fetched_at": now_iso
                }).execute()
                return
            except Exception as e:
                print(f"[DB] Supabase cache save error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO search_cache (id, ticker, source, payload, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (cache_id, ticker, source, json.dumps(payload), now_iso)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] SQLite cache save error: {e}")

    def save_training_rows(self, rows: List[Dict[str, Any]]):
        import uuid
        if not rows:
            return
        if self.use_supabase:
            try:
                self.supabase.table("training_data").insert(rows).execute()
                return
            except Exception as e:
                print(f"[DB] Supabase save_training_rows error: {e}")

        # SQLite fallback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for r in rows:
            cursor.execute(
                "INSERT INTO training_data (id, ticker, headline, headline_date, price_up_next_day) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), r["ticker"], r["headline"], str(r["headline_date"]), int(r["price_up_next_day"]))
            )
        conn.commit()
        conn.close()

    def load_training_data(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            try:
                res = self.supabase.table("training_data").select("*").execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"[DB] Supabase load_training_data error: {e}")

        # SQLite fallback
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, headline, headline_date, price_up_next_day FROM training_data")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_ticker_resolution(self, raw_query: str) -> Optional[str]:
        raw_key = raw_query.strip().lower()
        if self.use_supabase:
            try:
                res = self.supabase.table("ticker_resolution_cache") \
                    .select("resolved_ticker") \
                    .eq("raw_query", raw_key) \
                    .limit(1) \
                    .execute()
                if res.data:
                    return res.data[0]["resolved_ticker"]
            except Exception as e:
                print(f"[DB] Supabase resolution fetch error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT resolved_ticker FROM ticker_resolution_cache WHERE raw_query=?", (raw_key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception as e:
            print(f"[DB] SQLite resolution fetch error: {e}")
        return None

    def save_ticker_resolution(self, raw_query: str, resolved_ticker: str):
        import uuid
        raw_key = raw_query.strip().lower()
        res_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()

        if self.use_supabase:
            try:
                self.supabase.table("ticker_resolution_cache").upsert({
                    "raw_query": raw_key,
                    "resolved_ticker": resolved_ticker,
                    "resolved_at": now_iso
                }).execute()
                return
            except Exception as e:
                print(f"[DB] Supabase resolution save error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ticker_resolution_cache (id, raw_query, resolved_ticker, resolved_at) VALUES (?, ?, ?, ?)",
                (res_id, raw_key, resolved_ticker, now_iso)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] SQLite resolution save error: {e}")

    def create_alert(self, ticker: str, target_price: float, condition: str, currency_symbol: str = "$", user_id: str = "guest") -> Dict[str, Any]:
        import uuid
        alert_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()
        clean_ticker = ticker.strip().upper()
        clean_cond = "above" if "above" in condition.lower() else "below"

        record = {
            "id": alert_id,
            "ticker": clean_ticker,
            "target_price": float(target_price),
            "condition": clean_cond,
            "currency_symbol": currency_symbol,
            "status": "active",
            "user_id": user_id,
            "created_at": now_iso,
            "triggered_at": None
        }

        if self.use_supabase:
            try:
                self.supabase.table("price_alerts").insert(record).execute()
                return record
            except Exception as e:
                print(f"[DB] Supabase create alert error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO price_alerts (id, ticker, target_price, condition, currency_symbol, status, user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (alert_id, clean_ticker, float(target_price), clean_cond, currency_symbol, "active", user_id, now_iso)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] SQLite create alert error: {e}")

        return record

    def get_alerts(self, status: str = "active", user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_supabase:
            try:
                query = self.supabase.table("price_alerts").select("*").eq("status", status)
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.order("created_at", desc=True).execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"[DB] Supabase get alerts error: {e}")

        # SQLite fallback
        results = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM price_alerts WHERE status=?"
            params = [status]
            if user_id:
                query += " AND user_id=?"
                params.append(user_id)
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for r in rows:
                results.append(dict(r))
            conn.close()
        except Exception as e:
            print(f"[DB] SQLite get alerts error: {e}")
        return results

    def trigger_alert(self, alert_id: str) -> bool:
        now_iso = datetime.utcnow().isoformat()
        if self.use_supabase:
            try:
                self.supabase.table("price_alerts").update({
                    "status": "triggered",
                    "triggered_at": now_iso
                }).eq("id", alert_id).execute()
                return True
            except Exception as e:
                print(f"[DB] Supabase trigger alert error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE price_alerts SET status='triggered', triggered_at=? WHERE id=?", (now_iso, alert_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] SQLite trigger alert error: {e}")
            return False

    def delete_alert(self, alert_id: str) -> bool:
        if self.use_supabase:
            try:
                self.supabase.table("price_alerts").delete().eq("id", alert_id).execute()
                return True
            except Exception as e:
                print(f"[DB] Supabase delete alert error: {e}")

        # SQLite fallback
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] SQLite delete alert error: {e}")
            return False

db_client = DatabaseClient()

