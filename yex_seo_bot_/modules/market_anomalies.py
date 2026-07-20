"""Market anomaly detector via CoinGecko/CoinGlass - pure Python path."""
import logging
import requests
from config.settings import (
    TRACKED_COINS, PRICE_CHANGE_THRESHOLD_24H,
    VOLUME_SPIKE_MULTIPLIER, FUNDING_RATE_EXTREME,
)
from modules.state import is_seen, mark_seen, record_price, get_price_baseline
from modules.intelligence import interpret_signal
from modules.telegram_client import send_alert

log = logging.getLogger(__name__)
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGLASS_FUNDING_URL = "https://open-api.coinglass.com/public/v2/funding"


def check_prices():
    try:
        resp = requests.get(COINGECKO_URL, params={
            "vs_currency": "usd", "ids": ",".join(TRACKED_COINS),
            "price_change_percentage": "1h,24h,7d",
        }, timeout=20)
        resp.raise_for_status()
        coins = resp.json()
    except Exception as e:
        log.error("CoinGecko fetch failed: %s", e)
        return

    for coin in coins:
        cid = coin["id"]
        price = coin["current_price"]
        volume = coin["total_volume"]
        change_24h = coin.get("price_change_percentage_24h", 0) or 0
        record_price(cid, price, volume)

        avg_price, avg_volume = get_price_baseline(cid, days=7)
        anomalies = []
        if abs(change_24h) >= PRICE_CHANGE_THRESHOLD_24H:
            direction = "surged" if change_24h > 0 else "dropped"
            anomalies.append(f"Price {direction} {abs(change_24h):.1f}% in 24h")
        if avg_volume and volume >= avg_volume * VOLUME_SPIKE_MULTIPLIER:
            mult = volume / avg_volume
            anomalies.append(f"Volume {mult:.1f}x above 7-day average")
        if not anomalies:
            continue

        sig = f"{cid}:{'+'.join(anomalies)}"
        if is_seen("market:price", sig):
            continue
        mark_seen("market:price", sig)

        signal = {
            "coin": coin["name"], "symbol": coin["symbol"].upper(), "price_usd": price,
            "change_1h": coin.get("price_change_percentage_1h_in_currency"),
            "change_24h": change_24h, "change_7d": coin.get("price_change_percentage_7d_in_currency"),
            "volume_24h": volume, "anomalies": anomalies,
            "market_cap_rank": coin.get("market_cap_rank"),
        }
        verdict = interpret_signal("market_anomaly", signal)
        if verdict.get("skip"):
            continue
        send_alert(module=f"Market:{coin['symbol'].upper()}", priority=verdict["priority"],
                   title=verdict["title"], body=verdict["summary"], action=verdict["angle"])


def check_funding():
    try:
        resp = requests.get(COINGLASS_FUNDING_URL, params={"symbol": "BTC"}, timeout=20)
        if resp.status_code != 200:
            return
        data = resp.json()
    except Exception as e:
        log.debug("CoinGlass funding fetch failed: %s", e)
        return

    try:
        rates = data.get("data", [])
        for exchange_data in rates[:5]:
            rate = exchange_data.get("rate", 0)
            if abs(rate) >= FUNDING_RATE_EXTREME:
                exch = exchange_data.get("exchangeName", "unknown")
                sig = f"funding:BTC:{exch}:{round(rate, 3)}"
                if is_seen("market:funding", sig):
                    continue
                mark_seen("market:funding", sig)
                signal = {
                    "asset": "BTC", "exchange": exch, "funding_rate_pct": rate,
                    "interpretation": "negative = shorts paying, possible squeeze setup"
                                       if rate < 0 else "extreme long bias, liquidation risk",
                }
                verdict = interpret_signal("funding_extreme", signal)
                if verdict.get("skip"):
                    continue
                send_alert(module="Market:Funding", priority=verdict["priority"],
                          title=verdict["title"], body=verdict["summary"], action=verdict["angle"])
    except Exception as e:
        log.debug("Funding rate parse failed: %s", e)


def run():
    log.info("Market anomaly scan starting")
    check_prices()
    check_funding()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
