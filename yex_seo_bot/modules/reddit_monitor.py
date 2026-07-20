"""Reddit trends monitor - pure Python path."""
import logging
import praw
from config.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, SUBREDDITS
from modules.state import is_seen, mark_seen
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)
_reddit = None


def get_reddit():
    global _reddit
    if _reddit is None:
        if not REDDIT_CLIENT_ID:
            raise RuntimeError("Reddit credentials missing")
        _reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID, client_secret=REDDIT_CLIENT_SECRET,
                              user_agent=REDDIT_USER_AGENT)
    return _reddit


def run():
    log.info("Reddit trends scan starting")
    try:
        reddit = get_reddit()
    except Exception as e:
        log.error("Reddit init failed: %s", e)
        return

    candidates = []
    for sub_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.hot(limit=15):
                if post.score < 200:
                    continue
                if is_seen(f"reddit:{sub_name}", post.id):
                    continue
                mark_seen(f"reddit:{sub_name}", post.id, post.title, post.url)
                candidates.append({
                    "subreddit": sub_name, "title": post.title, "score": post.score,
                    "num_comments": post.num_comments,
                    "url": f"https://reddit.com{post.permalink}",
                    "selftext": (post.selftext or "")[:400],
                })
        except Exception as e:
            log.error("Subreddit fetch failed %s: %s", sub_name, e)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    for item in candidates[:5]:
        verdict = interpret_signal("reddit_trending", item)
        if verdict.get("skip"):
            continue
        send_alert(module=f"Reddit:r/{item['subreddit']}", priority=verdict["priority"],
                   title=verdict["title"], body=verdict["summary"],
                   url=item["url"], action=verdict["angle"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
