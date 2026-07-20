"""Token unlock tracker via DefiLlama - pure Python path."""
import logging
import requests
from datetime import datetime, timedelta
from modules.state import is_seen, mark_seen
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)
DEFILLAMA_UNLOCKS = "https://api.llama.fi/emissions"


def run():
    log.info("Token unlocks scan starting")
    try:
        resp = requests.get(DEFILLAMA_UNLOCKS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.error("DefiLlama unlocks fetch failed: %s", e)
        return

    now = datetime.utcnow()
    week_out = now + timedelta(days=7)
    upcoming = []

    for token in data if isinstance(data, list) else data.get("emissions", []):
        try:
            events = token.get("upcomingEvent", [])
            for event in events:
                ts = event.get("timestamp")
                if not ts:
                    continue
                event_time = datetime.utcfromtimestamp(ts)
                if not (now <= event_time <= week_out):
                    continue
                amount_usd = event.get("amountInUSD", 0)
                if amount_usd < 5_000_000:
                    continue
                upcoming.append({
                    "token": token.get("name"), "symbol": token.get("symbol"),
                    "unlock_time": event_time.isoformat(), "amount_usd": amount_usd,
                    "percent_of_supply": event.get("noOfTokens", 0),
                })
        except Exception:
            continue

    upcoming.sort(key=lambda x: x["amount_usd"], reverse=True)
    for unlock in upcoming[:5]:
        sig = f"unlock:{unlock['symbol']}:{unlock['unlock_time']}"
        if is_seen("unlock", sig):
            continue
        mark_seen("unlock", sig)
        verdict = interpret_signal("token_unlock", unlock)
        if verdict.get("skip"):
            continue
        send_alert(module=f"Unlock:{unlock['symbol']}", priority=verdict.get("priority", "OPPORTUNITY"),
                  title=verdict["title"], body=verdict["summary"], action=verdict["angle"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
