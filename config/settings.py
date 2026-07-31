"""
YEX SEO Content Intelligence Bot - Configuration
All API keys are read from environment variables (.env file).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ============================================================
# TELEGRAM
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ============================================================
# OPENAI (GPT for interpretation)
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# ============================================================
# DATA SOURCES
# ============================================================
RSS_FEEDS = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "The Block": "https://www.theblock.co/rss.xml",
    "BeInCrypto": "https://beincrypto.com/feed/",
    "Decrypt": "https://decrypt.co/feed",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "CryptoSlate": "https://cryptoslate.com/feed/",
}

SUBREDDITS = [
    "cryptocurrency", "Bitcoin", "ethereum",
    "CryptoMarkets", "defi", "CryptoCurrencyTrading",
]

COMPETITOR_FEEDS = {
    "Binance Academy": "https://academy.binance.com/en/rss.xml",
    "Bybit Learn": "https://learn.bybit.com/rss/",
}

TRENDS_SEEDS = [
    "bitcoin", "ethereum", "crypto", "altcoin", "defi",
    "stablecoin", "memecoin", "tokenized stocks", "rwa crypto",
    "perpetual futures", "crypto staking",
]

TRACKED_COINS = [
    "bitcoin", "ethereum", "solana", "binancecoin", "ripple",
    "cardano", "avalanche-2", "chainlink", "polkadot", "dogecoin",
]

PRICE_CHANGE_THRESHOLD_24H = 5.0
VOLUME_SPIKE_MULTIPLIER = 2.5
FUNDING_RATE_EXTREME = 0.05

# ============================================================
# GOOGLE SEARCH CONSOLE
# ============================================================
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "sc-domain:yex.com")
GSC_CREDENTIALS_PATH = BASE_DIR / "config" / "gsc_credentials.json"

# ============================================================
# REDDIT API
# ============================================================
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = "yex_seo_bot/1.0 by /u/yourusername"

# ============================================================
# SCHEDULING (in minutes) - used by the pure-Python main.py path.
# If you're running the n8n hybrid, scheduling lives in n8n instead.
# ============================================================
SCHEDULES = {
    "rss_news":          15,
    "market_anomalies":  30,
    "reddit_trends":     60,
    "google_trends":     360,
    "competitor_watch":  720,
    "gsc_performance":   1440,
    "token_unlocks":     1440,
    "daily_digest":      1440,
}

STATE_DB = BASE_DIR / "data" / "state.db"
LOG_FILE = BASE_DIR / "logs" / "bot.log"

PRIORITY = {
    "URGENT":   "🔴",
    "OPPORTUNITY": "🟡",
    "MONITOR":  "🔵",
    "INSIGHT":  "🟢",
}

EDITORIAL_CONTEXT = os.getenv("EDITORIAL_CONTEXT", """
You are advising the SEO content team at a regulated crypto trading platform.
The audience is active crypto traders.

Editorial standards:
- Follow the platform's competitor-mention policy (configurable per client)
- Short, punchy sentences for a trader audience
- Consistent brand voice as defined by the client
- Focus on actionable angles: what should the trader DO with this info?

When suggesting content angles, prioritize:
1. Topics where the platform's core features are relevant (e.g. futures,
   margin, copy trading, staking, tokenized assets)
2. Search opportunities (rising queries, low-competition keywords)
3. Educational gaps in the content cluster
4. Reactive recap angles for a weekly market roundup
""")
