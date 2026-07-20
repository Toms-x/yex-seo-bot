"""Competitor content tracker - pure Python path."""
import logging
import feedparser
from config.settings import COMPETITOR_FEEDS
from modules.state import is_seen, mark_seen
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)


def run():
    log.info("Competitor watch starting")
    new_competitor_content = []
    for source, url in COMPETITOR_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                entry_id = entry.get("id") or entry.get("link")
                if not entry_id or is_seen(f"competitor:{source}", entry_id):
                    continue
                mark_seen(f"competitor:{source}", entry_id, entry.title, entry.link)
                new_competitor_content.append({
                    "competitor": source, "title": entry.title, "url": entry.link,
                    "summary": entry.get("summary", "")[:400],
                })
        except Exception as e:
            log.error("Competitor feed failed %s: %s", source, e)

    if not new_competitor_content:
        return

    signal = {
        "new_competitor_articles": new_competitor_content,
        "instruction": ("Identify content gaps for YEX. Which of these topics is YEX missing? "
                        "Which deserves a stronger angle? Remember: never name competitors in "
                        "the suggested YEX content."),
    }
    verdict = interpret_signal("competitor_publishing", signal)
    if verdict.get("skip"):
        return
    send_alert(module="Competitor:Gap", priority=verdict.get("priority", "OPPORTUNITY"),
              title=verdict["title"], body=verdict["summary"], action=verdict["angle"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
