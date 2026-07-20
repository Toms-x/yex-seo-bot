"""Daily morning digest - pure Python path."""
import logging
from modules.state import get_recent_alerts
from modules.intelligence import synthesize_digest
from modules.telegram_client import send_digest

log = logging.getLogger(__name__)


def run():
    log.info("Daily digest starting")
    alerts = get_recent_alerts(hours=24)
    if not alerts:
        send_digest("Morning briefing",
                    "No significant signals in past 24h. Quiet market - good day to catch up "
                    "on backlog content (tokenized stocks cluster, RWA explainers).")
        return
    briefing = synthesize_digest(alerts)
    send_digest("Morning briefing", briefing)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
