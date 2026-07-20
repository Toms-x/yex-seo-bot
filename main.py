"""
Main scheduler for the PURE PYTHON path.

If you're running the n8n hybrid setup (docker-compose.yml + n8n_workflows/),
you do NOT need this file - n8n handles scheduling instead, and calls the
FastAPI service in service/main.py directly.

Keep this as a fallback / for modules you haven't ported to n8n yet.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import SCHEDULES, LOG_FILE
from modules.state import init_db, cleanup_old_items
from modules import (
    rss_monitor, market_anomalies, reddit_monitor, trends_monitor,
    gsc_performance, competitor_watch, unlocks_monitor, daily_digest,
)
from modules.telegram_client import send_digest


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)
    root.addHandler(stdout)


def safe_run(name, fn):
    def wrapped():
        log = logging.getLogger(name)
        log.info("=== %s START ===", name)
        try:
            fn()
            log.info("=== %s OK ===", name)
        except Exception as e:
            log.exception("=== %s FAILED: %s ===", name, e)
    return wrapped


def main():
    setup_logging()
    log = logging.getLogger("scheduler")
    log.info("Initializing database")
    init_db()

    log.info("Starting scheduler")
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(safe_run("rss", rss_monitor.run), "interval",
                      minutes=SCHEDULES["rss_news"], id="rss")
    scheduler.add_job(safe_run("market", market_anomalies.run), "interval",
                      minutes=SCHEDULES["market_anomalies"], id="market")
    scheduler.add_job(safe_run("reddit", reddit_monitor.run), "interval",
                      minutes=SCHEDULES["reddit_trends"], id="reddit")
    scheduler.add_job(safe_run("trends", trends_monitor.run), "interval",
                      minutes=SCHEDULES["google_trends"], id="trends")
    scheduler.add_job(safe_run("competitor", competitor_watch.run), "interval",
                      minutes=SCHEDULES["competitor_watch"], id="competitor")
    scheduler.add_job(safe_run("gsc", gsc_performance.run), "interval",
                      minutes=SCHEDULES["gsc_performance"], id="gsc")
    scheduler.add_job(safe_run("unlocks", unlocks_monitor.run), "interval",
                      minutes=SCHEDULES["token_unlocks"], id="unlocks")
    scheduler.add_job(safe_run("digest", daily_digest.run),
                      CronTrigger(hour=7, minute=0), id="digest")
    scheduler.add_job(lambda: cleanup_old_items(30),
                      CronTrigger(day_of_week="sun", hour=3), id="cleanup")

    log.info("Scheduler started. Jobs: %s", [j.id for j in scheduler.get_jobs()])
    send_digest("Bot online", "YEX SEO intelligence bot is running. First signals incoming.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler shutting down")


if __name__ == "__main__":
    main()
