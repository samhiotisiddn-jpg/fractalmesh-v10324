#!/usr/bin/env python3
"""FRACTALMESH v10332.2 AI Scrape Agent (secrets-free). Reads creds from env.
Drains recent scrape_snapshot rows from the DB and stores AI summaries as
semantic_memory. In offline mode (no NEON_DSN) it just heartbeats gracefully.
"""
import os, json, time, logging, requests
from _agent_common import log_semantic, log_episodic

logging.basicConfig(level=logging.INFO, format="%(asctime)s | AISC | %(levelname)s | %(message)s")
logger = logging.getLogger("AIScrape")

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
GROQ_KEY = os.getenv("GROQ_KEY", "")
NEON_DSN = os.getenv("NEON_DSN", "")
INTERVAL = int(os.getenv("AISCRAPE_INTERVAL", "120"))

try:
    import psycopg2
    HAS_PG = True
except Exception:
    psycopg2 = None
    HAS_PG = False


def ai_summarize(text, provider="openrouter"):
    text = (text or "")[:4000]
    model = "meta-llama/llama-3.1-70b-instruct"
    url = "https://openrouter.ai/api/v1/chat/completions"
    key = OPENROUTER_KEY
    if provider == "groq":
        model = "llama-3.1-70b-versatile"
        url = "https://api.groq.com/openai/v1/chat/completions"
        key = GROQ_KEY
    if not key:
        logger.info("No LLM key configured; skipping summarization.")
        return ""
    try:
        r = requests.post(url,
                          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                          json={"model": model, "messages": [{"role": "user", "content": "Summarize concisely: " + text}]}, timeout=30)
        d = r.json() if str(r.status_code).startswith("2") else {}
        return d.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.warning("AI summarize error: %s", e)
        return ""


def drain_and_summarize():
    if not (NEON_DSN and HAS_PG):
        return 0
    try:
        with psycopg2.connect(NEON_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, payload FROM episodic_memory WHERE event_type='scrape_snapshot' ORDER BY timestamp DESC LIMIT 5")
                rows = cur.fetchall()
        processed = 0
        for rid, payload in rows:
            data = payload if isinstance(payload, dict) else json.loads(payload)
            url = data.get("url", "")
            fc = data.get("firecrawl", {})
            md = (fc.get("data", {}) or {}).get("markdown", "") if isinstance(fc, dict) else ""
            if not md:
                continue
            summary = ai_summarize(md)
            if summary:
                log_semantic(summary, {"source_url": url, "agent": "aiscrape", "ts": time.time()})
                processed += 1
        logger.info("Drained %d scrape(s) -> %d semantic summary(ies)", len(rows), processed)
        return processed
    except Exception as e:
        logger.error("Drain error: %s", e)
        return 0


def run():
    logger.info("[+] AI Scrape Agent started (interval=%ss) providers=%s", INTERVAL, bool(OPENROUTER_KEY) or bool(GROQ_KEY))
    while True:
        try:
            if NEON_DSN and HAS_PG:
                drain_and_summarize()
            else:
                log_episodic("aiscrape_heartbeat", {"status": "alive", "providers": bool(OPENROUTER_KEY) or bool(GROQ_KEY), "ts": time.time()}, importance=0.2)
        except Exception as e:
            logger.error("Cycle error: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--summarize" in os.sys.argv:
        import sys
        print(ai_summarize(sys.argv[sys.argv.index("--summarize") + 1]))
    else:
        run()
