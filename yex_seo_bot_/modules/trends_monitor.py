"""Google Trends rising queries monitor - pure Python path."""
import logging
import time
from pytrends.request import TrendReq
from config.settings import TRENDS_SEEDS
from modules.state import is_seen, mark_seen
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)


def run():
    log.info("Google Trends scan starting")
    try:
        pytrends = TrendReq(hl="en-US", tz=0)
    except Exception as e:
        log.error("Pytrends init failed: %s", e)
        return

    for seed in TRENDS_SEEDS:
        try:
            pytrends.build_payload([seed], timeframe="now 7-d", geo="")
            related = pytrends.related_queries()
            rising = related.get(seed, {}).get("rising")
            if rising is None or rising.empty:
                continue

            for _, row in rising.head(3).iterrows():
                query = row["query"]
                growth = row["value"]
                sig = f"trends:{seed}:{query}"
                if is_seen("trends:rising", sig):
                    continue
                mark_seen("trends:rising", sig)

                signal = {"seed_topic": seed, "rising_query": query, "growth": str(growth),
                         "note": "Rising search interest in past 7 days"}
                verdict = interpret_signal("rising_search_query", signal)
                if verdict.get("skip"):
                    continue
                send_alert(module="Trends:Google", priority=verdict["priority"],
                          title=verdict["title"], body=verdict["summary"], action=verdict["angle"])

            time.sleep(5)
        except Exception as e:
            log.error("Trends fetch failed for '%s': %s", seed, e)
            time.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
