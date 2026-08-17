#!/usr/bin/env python3
"""FRACTALMESH v10332.2 NFT Agent (secrets-free). Reads creds from env."""
import os, json, time, logging, requests
from _agent_common import log_episodic

logging.basicConfig(level=logging.INFO, format="%(asctime)s | NFT | %(levelname)s | %(message)s")
logger = logging.getLogger("NFT")

WAX_ACC = os.getenv("WAX_ACC", "")
ALCHEMY = os.getenv("ALCHEMY", "")
ETH_ADDR = os.getenv("ETH_ADDR", "")
OPENSEA = os.getenv("OPENSEA", "")
INTERVAL = int(os.getenv("NFT_INTERVAL", "120"))


def alchemy_nfts():
    if not (ALCHEMY and ETH_ADDR):
        return {}
    try:
        r = requests.get(f"https://eth-mainnet.g.alchemy.com/nft/v3/{ALCHEMY}/getNFTsForOwner?owner={ETH_ADDR}&withMetadata=true", timeout=15)
        return r.json()
    except Exception as e:
        logger.warning("Alchemy NFT error: %s", e)
        return {}


def open_sea_events():
    if not OPENSEA:
        return {}
    try:
        r = requests.get("https://api.opensea.io/api/v1/events?only_opensea=false&limit=20",
                         headers={"X-API-KEY": OPENSEA}, timeout=10)
        return r.json()
    except Exception as e:
        logger.warning("OpenSea error: %s", e)
        return {}


def wax_ram_price():
    try:
        r = requests.post("https://wax.greymass.com/v1/chain/get_table_rows",
                          json={"json": True, "code": "eosio", "scope": "eosio", "table": "rammarket", "limit": 1}, timeout=10)
        rows = r.json().get("rows", [])
        if rows:
            quote = float(rows[0]["quote"]["balance"].split()[0])
            base = float(rows[0]["base"]["balance"].split()[0])
            return quote / base if base else 0
        return 0
    except Exception as e:
        logger.warning("WAX RAM error: %s", e)
        return 0


def run():
    logger.info("[+] NFT Agent started (interval=%ss)", INTERVAL)
    while True:
        try:
            payload = {"alchemy_nfts": alchemy_nfts(), "opensea_events": open_sea_events(),
                       "wax_ram_price": wax_ram_price(), "wax_acc": WAX_ACC if WAX_ACC else None, "ts": time.time()}
            log_episodic("nft_snapshot", payload, importance=0.4)
            logger.info("NFT cycle done. RAM=%.6f WAX", payload["wax_ram_price"])
        except Exception as e:
            logger.error("Cycle error: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--once" in os.sys.argv:
        payload = {"alchemy_nfts": alchemy_nfts(), "opensea_events": open_sea_events(), "wax_ram_price": wax_ram_price(), "ts": time.time()}
        log_episodic("nft_snapshot", payload, importance=0.4)
        print(json.dumps({k: ("<redacted>" if k not in ("wax_ram_price",) else v) for k, v in payload.items()}, indent=2))
    else:
        run()
