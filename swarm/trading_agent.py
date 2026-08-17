#!/usr/bin/env python3
"""FRACTALMESH v10332.2 Trading Agent (secrets-free). Reads creds from env."""
import os, json, time, hmac, hashlib, base64, logging, requests
from _agent_common import log_episodic, log_revenue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | TRADE | %(levelname)s | %(message)s")
logger = logging.getLogger("Trading")

PIONEX_KEY = os.getenv("PIONEX_KEY", "")
PIONEX_SECRET = os.getenv("PIONEX_SECRET", "")
KUCOIN_KEY = os.getenv("KUCOIN_KEY", "")
KUCOIN_SECRET = os.getenv("KUCOIN_SECRET", "")
KUCOIN_PASS = os.getenv("KUCOIN_PASS", "")
COINGECKO = os.getenv("COINGECKO", "")
INTERVAL = int(os.getenv("TRADE_INTERVAL", "60"))
BTC_THRESHOLD = float(os.getenv("BTC_SURGE_THRESHOLD", "80000"))


def coin_gecko_price(ids="bitcoin,ethereum"):
    if not COINGECKO:
        return {}
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    data = None
    if COINGECKO:
        from urllib.parse import urlencode
        url += "&" + urlencode({"x_cg_demo_api_key": COINGECKO})
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        logger.warning("Coingecko error: %s", e)
    return data or {}


def pioneer_balances():
    if not (PIONEX_KEY and PIONEX_SECRET):
        return {}
    try:
        ts = str(int(time.time() * 1000))
        sig = hmac.new(PIONEX_SECRET.encode(), (ts + "GET" + "/api/v1/account/balances").encode(), hashlib.sha256).hexdigest()
        r = requests.get("https://api.pionex.com/api/v1/account/balances",
                         headers={"PIONEX-KEY": PIONEX_KEY, "PIONEX-SIGNATURE": sig, "PIONEX-TIMESTAMP": ts}, timeout=10)
        return r.json()
    except Exception as e:
        logger.warning("Pionex error: %s", e)
        return {}


def kucoin_balances():
    if not (KUCOIN_KEY and KUCOIN_SECRET and KUCOIN_PASS):
        return {}
    try:
        ts = str(int(time.time() * 1000))
        sig = base64.b64encode(hmac.new(KUCOIN_SECRET.encode(), (ts + "GET" + "/api/v1/accounts").encode(), hashlib.sha256).digest()).decode()
        r = requests.get("https://api.kucoin.com/api/v1/accounts",
                         headers={"KC-API-KEY": KUCOIN_KEY, "KC-API-SIGN": sig, "KC-API-TIMESTAMP": ts,
                                  "KC-API-PASSPHRASE": KUCOIN_PASS, "KC-API-KEY-VERSION": "2"}, timeout=10)
        return r.json()
    except Exception as e:
        logger.warning("KuCoin error: %s", e)
        return {}


def run_once():
    prices = coin_gecko_price()
    p = pioneer_balances()
    k = kucoin_balances()
    snapshot = {"prices": prices, "pionex": p, "kucoin": k, "ts": time.time()}
    log_episodic("trading_snapshot", snapshot, importance=0.5)
    if prices.get("bitcoin"):
        btc = prices["bitcoin"].get("usd", 0)
        if btc > BTC_THRESHOLD:
            log_revenue("trading_agent", "btc_surge", float(btc) * 0.001, {"trigger": f"btc_above_{int(BTC_THRESHOLD)}"})
    logger.info("Cycle done. BTC=%s", prices.get("bitcoin", {}).get("usd", "n/a"))


def run():
    logger.info("[+] Trading Agent started (interval=%ss)", INTERVAL)
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error("Cycle error: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--once" in os.sys.argv:
        run_once()
    else:
        run()
