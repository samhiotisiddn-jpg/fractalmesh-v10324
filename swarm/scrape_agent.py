#!/usr/bin/env python3
"""FRACTALMESH v10332.2 Scrape Agent (secrets-free). Reads creds from env."""
import os, json, time, logging, requests
from urllib.parse import quote
from _agent_common import log_episodic

logging.basicConfig(level=logging.INFO, format="%(asctime)s | SCRAPE | %(levelname)s | %(message)s")
logger = logging.getLogger("Scrape")

FIRECRAWL = os.getenv("FIRECRAWL", "")
CRAWLBASE = os.getenv("CRAWLBASE", "")
BROWSERBASE = os.getenv("BROWSERBASE", "")
INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "75"))
TARGETS = (os.getenv("SCRAPE_TARGETS", "https://news.ycombinator.com|https://github.com/trending")
           .split("|"))


def fetch_firecrawl(url):
    if not FIRECRAWL:
        return {}
    try:
        r = requests.post("https://api.firecrawl.dev/v1/scrape",
                          headers={"Authorization": "Bearer " + FIRECRAWL, "Content-Type": "application/json"},
                          json={"url": url, "formats": ["markdown"]}, timeout=20)
        if str(r.status_code).startswith("2"):
            return r.json()
        return {"http_status": r.status_code}
    except Exception as e:
        logger.warning("Firecrawl error: %s", e)
        return {}


def fetch_crawlbase(url):
    if not CRAWLBASE:
        return {}
    try:
        r = requests.get(f"https://api.crawlbase.com/?token={CRAWLBASE}&url={quote(url)}", timeout=20)
        return {"status_code": r.status_code, "content_len": len(r.text)}
    except Exception as e:
        logger.warning("Crawlbase error: %s", e)
        return {}


def run():
    logger.info("[+] Scrape Agent started. targets=%s", TARGETS)
    idx = 0
    while True:
        try:
            url = TARGETS[idx % len(TARGETS)]
            fc = fetch_firecrawl(url)
            cb = fetch_crawlbase(url)
            log_episodic("scrape_snapshot", {"url": url, "firecrawl": fc, "crawlbase": cb, "ts": time.time()}, importance=0.35)
            logger.info("Scraped %s (fc=%s cb=%s)", url, bool(fc), bool(cb))
        except Exception as e:
            logger.error("Cycle error: %s", e)
        idx += 1
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--once" in os.sys.argv:
        url = TARGETS[0]
        print(json.dumps({"target": url, "firecrawl": fetch_firecrawl(url), "crawlbase": fetch_crawlbase(url)}, indent=2))
    else:
        run()
