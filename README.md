# YEX SEO Intelligence Bot

A modular signal bot that turns crypto news, market anomalies, search trends,
and your own SEO performance into actionable Telegram alerts with specific
content angles — not just noise.

## Two ways to run this

**Option A — Pure Python** (original design)
Everything runs as Python modules on a schedule via APScheduler, packaged as
a systemd service. Simple, one language, no Docker needed.
→ See `README_PYTHON.md`

**Option B — n8n Hybrid** (recommended if you want visual debugging + easy tuning)
n8n handles scheduling, data fetching, and Telegram delivery. A small Python
FastAPI service handles the GPT-4o interpretation logic and dedup state.
→ See `N8N_SETUP.md`

Both share the same `modules/intelligence.py` (the GPT-4o prompt) and
`modules/state.py` (dedup logic) — pick whichever orchestration layer fits
how you like to work. You can even run both side by side while you migrate
module by module.

## Project structure

```
config/settings.py       # All thresholds, feeds, schedules - edit here to tune
modules/
  state.py                # SQLite dedup + price history + alert log
  intelligence.py          # GPT-4o prompt - the actual "brain"
  telegram_client.py       # Telegram delivery (pure-Python path only)
  rss_monitor.py           # News signal source
  market_anomalies.py      # Price/volume/funding signal source
  reddit_monitor.py        # Trending narrative signal source
  trends_monitor.py        # Google Trends rising queries
  gsc_performance.py       # Your own YEX content performance
  competitor_watch.py      # Competitor publishing gap analysis
  unlocks_monitor.py       # Token unlock calendar
  daily_digest.py          # Morning briefing synthesis
main.py                    # Pure-Python scheduler entrypoint

service/
  main.py                  # FastAPI wrapper for the n8n hybrid path
  Dockerfile

n8n_workflows/
  rss_monitor.json         # Importable template - replicate for other modules

docker-compose.yml         # Runs n8n + intelligence service (hybrid path)
yex-seo-bot.service        # systemd unit (pure-Python path)
```

## Quick start

Pick your path and follow the matching guide:
- Pure Python → `README_PYTHON.md`
- n8n Hybrid → `N8N_SETUP.md`

Both need the same first step: fill in `.env` from `.env.example` with your
Telegram bot token, chat ID, and Anthropic API key.
