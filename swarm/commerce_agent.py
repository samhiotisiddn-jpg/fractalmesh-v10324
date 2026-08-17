#!/usr/bin/env python3
"""FRACTALMESH v10332.2 Commerce Agent (secrets-free). Reads creds from env."""
import os, json, time, logging, requests
from _agent_common import log_episodic, log_revenue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | COMMERCE | %(levelname)s | %(message)s")
logger = logging.getLogger("Commerce")

STRIPE_SK = os.getenv("STRIPE_SECRET_KEY", "") or os.getenv("STRIPE_SK", "")
PRINTFUL = os.getenv("PRINTFUL", "")
GUMROAD = os.getenv("GUMROAD", "")
INTERVAL = int(os.getenv("COMMERCE_INTERVAL", "90"))


def stripe_balance():
    if not STRIPE_SK:
        return {}
    try:
        r = requests.get("https://api.stripe.com/v1/balance",
                         headers={"Authorization": "Bearer " + STRIPE_SK}, timeout=10)
        return r.json() if str(r.status_code).startswith("2") else {"http_status": r.status_code}
    except Exception as e:
        logger.warning("Stripe error: %s", e)
        return {}


def stripe_recent_charges():
    if not STRIPE_SK:
        return {}
    try:
        r = requests.get("https://api.stripe.com/v1/charges?limit=10",
                         headers={"Authorization": "Bearer " + STRIPE_SK}, timeout=10)
        return r.json() if str(r.status_code).startswith("2") else {"http_status": r.status_code}
    except Exception as e:
        logger.warning("Stripe charges error: %s", e)
        return {}


def printful_products():
    if not PRINTFUL:
        return {}
    try:
        r = requests.get("https://api.printful.com/store/products",
                         headers={"Authorization": "Bearer " + PRINTFUL}, timeout=10)
        return r.json()
    except Exception as e:
        logger.warning("Printful error: %s", e)
        return {}


def run():
    logger.info("[+] Commerce Agent started (interval=%ss)", INTERVAL)
    while True:
        try:
            bal = stripe_balance()
            charges = stripe_recent_charges()
            products = printful_products()
            total = 0.0
            if bal and "available" in bal:
                for item in bal.get("available", []):
                    if item.get("currency") == "usd":
                        total = item.get("amount", 0) / 100.0
            log_episodic("commerce_snapshot", {"stripe_balance_usd": total, "charges": charges, "products": products, "ts": time.time()}, importance=0.6)
            # Note: a *balance* is NOT realized revenue. We log only actual charge amounts.
            # (Kept out of auto-writing the ledger to avoid booking unrealized balance.)
            # For a defensible ledger, hook the Stripe webhook endpoint instead.
            logger.info("Commerce cycle. Stripe balance USD=%.2f", total)
        except Exception as e:
            logger.error("Cycle error: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--once" in os.sys.argv:
        bal = stripe_balance()
        total = sum(i.get("amount", 0) / 100.0 for i in bal.get("available", []) if i.get("currency") == "usd")
        log_episodic("commerce_snapshot", {"stripe_balance_usd": total, "ts": time.time()}, importance=0.6)
        print(json.dumps({"stripe_balance_usd": total}, indent=2))
    else:
        run()
