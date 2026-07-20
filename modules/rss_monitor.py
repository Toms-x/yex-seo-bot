"""RSS news monitor - pure Python path (superseded by n8n_workflows/rss_monitor.json in the hybrid setup)."""
import logging
import feedparser
from config.settings import RSS_FEEDS
from modules.state import is_seen, mark_seen
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)


def run():
    log.info("RSS scan starting")
    new_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                entry_id = entry.get("id") or entry.get("link")
                if not entry_id or is_seen(f"rss:{source}", entry_id):
                    continue
                mark_seen(f"rss:{source}", entry_id, entry.title, entry.link)
                new_items.append({
                    "source": source, "title": entry.title, "url": entry.link,
                    "summary": entry.get("summary", "")[:500],
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            log.error("RSS fetch failed for %s: %s", source, e)

    log.info("RSS scan: %d new items", len(new_items))
    for item in new_items:
        try:
            verdict = interpret_signal("crypto_news", item)
            if verdict.get("skip"):
                continue
            send_alert(
                module=f"News:{item['source']}", priority=verdict["priority"],
                title=verdict["title"], body=verdict["summary"],
                url=item["url"], action=verdict["angle"],
            )
        except Exception as e:
            log.error("Failed to process item %s: %s", item.get("title"), e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
