"""Google Search Console integration - pure Python path. See README for OAuth setup."""
import logging
import pickle
from datetime import date, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config.settings import GSC_SITE_URL, GSC_CREDENTIALS_PATH, BASE_DIR
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
TOKEN_PATH = BASE_DIR / "config" / "gsc_token.pickle"


def get_service():
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(GSC_CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return build("searchconsole", "v1", credentials=creds)


def fetch_period(service, start: date, end: date, dimensions: list):
    return service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": start.isoformat(), "endDate": end.isoformat(),
              "dimensions": dimensions, "rowLimit": 500},
    ).execute().get("rows", [])


def run():
    log.info("GSC performance scan starting")
    try:
        service = get_service()
    except Exception as e:
        log.error("GSC auth failed: %s", e)
        return

    today = date.today()
    recent_end = today - timedelta(days=3)
    recent_start = recent_end - timedelta(days=7)
    prior_end = recent_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=7)

    try:
        recent = fetch_period(service, recent_start, recent_end, ["query", "page"])
        prior = fetch_period(service, prior_start, prior_end, ["query", "page"])
    except Exception as e:
        log.error("GSC fetch failed: %s", e)
        return

    def index(rows):
        return {(r["keys"][0], r["keys"][1]): {
            "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0), "position": r.get("position", 100),
        } for r in rows}

    recent_idx = index(recent)
    prior_idx = index(prior)

    opportunities, decayed, big_wins = [], [], []

    for key, recent_data in recent_idx.items():
        query, page = key
        prior_data = prior_idx.get(key, {"impressions": 0, "position": 100, "clicks": 0})
        impr_delta = recent_data["impressions"] - prior_data["impressions"]
        pos_delta = prior_data["position"] - recent_data["position"]

        if 8 <= recent_data["position"] <= 20 and recent_data["impressions"] >= 50:
            if pos_delta >= 5:
                opportunities.append({
                    "query": query, "page": page,
                    "current_position": round(recent_data["position"], 1),
                    "prior_position": round(prior_data["position"], 1),
                    "impressions": recent_data["impressions"], "clicks": recent_data["clicks"],
                })

        if prior_data["impressions"] >= 200 and impr_delta <= -prior_data["impressions"] * 0.5:
            decayed.append({
                "page": page, "query": query, "impressions_before": prior_data["impressions"],
                "impressions_now": recent_data["impressions"],
                "loss_pct": round(abs(impr_delta) / prior_data["impressions"] * 100, 1),
            })

        if prior_data["impressions"] >= 100 and impr_delta >= prior_data["impressions"]:
            big_wins.append({"page": page, "query": query, "impressions_growth": impr_delta,
                            "current_clicks": recent_data["clicks"]})

    opportunities.sort(key=lambda x: x["impressions"], reverse=True)
    decayed.sort(key=lambda x: x["loss_pct"], reverse=True)
    big_wins.sort(key=lambda x: x["impressions_growth"], reverse=True)

    for opp in opportunities[:5]:
        verdict = interpret_signal("gsc_opportunity", opp)
        if verdict.get("skip"):
            continue
        send_alert(module="SEO:Opportunity", priority=verdict.get("priority", "OPPORTUNITY"),
                   title=verdict["title"], body=verdict["summary"], url=opp["page"], action=verdict["angle"])

    for win in big_wins[:3]:
        verdict = interpret_signal("gsc_winner", win)
        if verdict.get("skip"):
            continue
        send_alert(module="SEO:Winning", priority=verdict.get("priority", "INSIGHT"),
                   title=verdict["title"], body=verdict["summary"], url=win["page"], action=verdict["angle"])

    for d in decayed[:3]:
        verdict = interpret_signal("gsc_decay", d)
        if verdict.get("skip"):
            continue
        send_alert(module="SEO:Decay", priority=verdict.get("priority", "OPPORTUNITY"),
                   title=verdict["title"], body=verdict["summary"], url=d["page"], action=verdict["angle"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
