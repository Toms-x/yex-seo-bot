"""
State management - SQLite-based deduplication so we never alert on the same
news item, post, or signal twice. Survives restarts.
"""
import sqlite3
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from config.settings import STATE_DB


def init_db():
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_items (
                hash TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT,
                url TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_seen_at ON seen_items(seen_at);

            CREATE TABLE IF NOT EXISTS price_history (
                coin_id TEXT,
                price REAL,
                volume REAL,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (coin_id, captured_at)
            );

            CREATE TABLE IF NOT EXISTS gsc_baseline (
                query TEXT PRIMARY KEY,
                avg_position REAL,
                clicks INTEGER,
                impressions INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alerts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT,
                priority TEXT,
                title TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(STATE_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def is_seen(source: str, identifier: str) -> bool:
    h = _hash(f"{source}:{identifier}")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_items WHERE hash = ?", (h,)
        ).fetchone()
    return row is not None


def mark_seen(source: str, identifier: str, title: str = "", url: str = ""):
    h = _hash(f"{source}:{identifier}")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_items (hash, source, title, url) VALUES (?, ?, ?, ?)",
            (h, source, title, url),
        )


def cleanup_old_items(days: int = 30):
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_conn() as conn:
        conn.execute("DELETE FROM seen_items WHERE seen_at < ?", (cutoff,))
        conn.execute("DELETE FROM price_history WHERE captured_at < ?", (cutoff,))


def record_price(coin_id: str, price: float, volume: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO price_history (coin_id, price, volume) VALUES (?, ?, ?)",
            (coin_id, price, volume),
        )


def get_price_baseline(coin_id: str, days: int = 7):
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT AVG(price) as p, AVG(volume) as v FROM price_history "
            "WHERE coin_id = ? AND captured_at >= ?",
            (coin_id, cutoff),
        ).fetchone()
    return (row["p"], row["v"]) if row and row["p"] else (None, None)


def log_alert(module: str, priority: str, title: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alerts_log (module, priority, title) VALUES (?, ?, ?)",
            (module, priority, title),
        )


def get_recent_alerts(hours: int = 24):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT module, priority, title, sent_at FROM alerts_log "
            "WHERE sent_at >= ? ORDER BY sent_at DESC",
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]
