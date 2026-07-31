"""
GPT interpretation layer.

This is the brain. Raw signals are useless ("BTC dropped 5%"). The bot's value
comes from GPT reading the signal in context and outputting an actionable
content angle for the YEX SEO team.

Called either directly by pure-Python modules (main.py path), or via the
FastAPI wrapper in service/main.py when running the n8n hybrid setup.
"""
import logging
import json
from openai import OpenAI
from config.settings import (
    OPENAI_API_KEY, OPENAI_MODEL, EDITORIAL_CONTEXT
)

log = logging.getLogger(__name__)
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY missing in .env")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def interpret_signal(signal_type: str, raw_data: dict) -> dict:
    """
    Send a raw signal to Claude. Get back:
        {
            "priority": "URGENT|OPPORTUNITY|MONITOR|INSIGHT",
            "title": "Short headline for the alert",
            "summary": "1-2 sentence explanation of why this matters",
            "angle": "Specific content suggestion - what to write, what slug, what angle",
            "skip": false  # If signal is noise, skip alerting
        }
    """
    prompt = f"""{EDITORIAL_CONTEXT}

A signal just came in from the monitoring system.

Signal type: {signal_type}
Raw data:
{json.dumps(raw_data, indent=2, default=str)}

Decide:
1. Is this worth alerting John about? If it's noise (low-quality news, irrelevant,
   already covered, too speculative), set "skip": true.
2. If worth alerting, assign a priority:
   - URGENT: Breaking, time-sensitive, write today (major hack, regulatory action,
     market crash, big policy news)
   - OPPORTUNITY: Strong content opportunity this week (rising search trend,
     emerging narrative, competitor gap)
   - MONITOR: Worth knowing for context, but not actionable today
   - INSIGHT: Performance feedback on existing YEX content
3. Write a sharp 1-2 sentence summary.
4. Most important: write a SPECIFIC content angle. Not "write about X" — instead
   "Write a 1200-word piece titled 'Why funding rates flipped negative on ETH
   today and what it means for your next trade' — angle the YEX perpetuals
   product naturally." Be concrete.

Respond ONLY with valid JSON, no other text:
{{
  "skip": false,
  "priority": "OPPORTUNITY",
  "title": "...",
  "summary": "...",
  "angle": "..."
}}"""

    text = ""
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.error("GPT returned invalid JSON: %s | text: %s", e, text[:200])
        return {"skip": True}
    except Exception as e:
        log.error("GPT interpretation failed: %s", e)
        return {"skip": True}


def synthesize_digest(alerts: list, performance: dict = None) -> str:
    """
    Daily digest - Claude reads all alerts from past 24h plus GSC performance
    and produces a coherent morning briefing.
    """
    prompt = f"""{EDITORIAL_CONTEXT}

Below are all signals captured in the past 24 hours, plus YEX content performance.

Alerts ({len(alerts)} total):
{json.dumps(alerts, indent=2, default=str)}

Performance data:
{json.dumps(performance or {}, indent=2, default=str)}

Write a tight morning briefing for John (the SEO manager). Structure:

TODAY'S PRIORITIES (max 3 items, ranked by urgency)
- Each: what to write, why now, suggested slug

THIS WEEK'S OPPORTUNITIES (max 5 items)
- Rising trends, content gaps, narrative shifts

YEX PERFORMANCE NOTES
- Rankings movement, query wins, pages losing impressions

MARKET CONTEXT (2-3 lines)
- The narrative shaping the week

Keep it scannable. No filler. No em dashes. Plain text, no markdown.
Target: under 400 words total."""

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("Digest synthesis failed: %s", e)
        return f"Digest generation failed: {e}"
