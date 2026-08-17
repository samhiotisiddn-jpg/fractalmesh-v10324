#!/usr/bin/env python3
"""FRACTALMESH v10332.2 Social Agent (secrets-free). Reads creds from env."""
import os, json, time, logging, requests
from _agent_common import log_episodic

logging.basicConfig(level=logging.INFO, format="%(asctime)s | SOCIAL | %(levelname)s | %(message)s")
logger = logging.getLogger("Social")

TELEGRAM_BOT = os.getenv("TELEGRAM_BOT", "")
DEVTO = os.getenv("DEVTO", "")
INTERVAL = int(os.getenv("SOCIAL_INTERVAL", "45"))


def telegram_messages():
    if not TELEGRAM_BOT:
        return {}
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT}/getMe", timeout=10)
        return r.json()
    except Exception as e:
        logger.warning("Telegram error: %s", e)
        return {}


def devto_articles():
    if not DEVTO:
        return {}
    try:
        r = requests.get("https://dev.to/api/articles/me/all", headers={"api-key": DEVTO}, timeout=10)
        return r.json() if isinstance(r.json(), list) else {}
    except Exception as e:
        logger.warning("Dev.to error: %s", e)
        return {}


def run():
    logger.info("[+] Social Agent started (interval=%ss)", INTERVAL)
    while True:
        try:
            tg = telegram_messages()
            dev = devto_articles()
            payload = {"telegram_ok": bool(tg.get("ok")), "devto_articles": len(dev) if isinstance(dev, list) else 0, "ts": time.time()}
            log_episodic("social_snapshot", payload, importance=0.3)
            logger.info("Social cycle. Telegram=%s Dev.to=%d", payload["telegram_ok"], payload["devto_articles"])
        except Exception as e:
            logger.error("Cycle error: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--once" in os.sys.argv:
        tg = telegram_messages()
        dev = devto_articles()
        print(json.dumps({"telegram_ok": bool(tg.get("ok")), "devto_articles": len(dev) if isinstance(dev, list) else 0}, indent=2))
    else:
        run()
