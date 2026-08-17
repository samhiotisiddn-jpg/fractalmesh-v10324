#!/usr/bin/env python3
"""Shared helpers for FractalMesh agents: env-safe logging with graceful offline mode."""
import os, json, time, logging

logger = logging.getLogger("AgentCommon")
NEON_DSN = os.getenv("NEON_DSN", "")

try:
    import psycopg2
    HAS_PG = True
except Exception:
    psycopg2 = None
    HAS_PG = False


def log_episodic(event_type: str, payload: dict, importance=0.0):
    if not NEON_DSN or not HAS_PG:
        logger.debug("[offline] episodic %s dropped (no DB): %s", event_type, json.dumps(payload)[:200])
        return None
    try:
        with psycopg2.connect(NEON_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO episodic_memory (event_type, payload, importance_score) VALUES (%s,%s,%s)",
                    (event_type, json.dumps(payload), importance))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("episodic log failed (continuing): %s", e)
        return None


def log_semantic(content: str, metadata=None):
    if not NEON_DSN or not HAS_PG:
        logger.debug("[offline] semantic dropped (no DB)")
        return None
    try:
        with psycopg2.connect(NEON_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO semantic_memory (content, metadata) VALUES (%s,%s)",
                    (content, json.dumps(metadata or {})))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("semantic log failed (continuing): %s", e)
        return None


def log_revenue(source: str, revenue_type: str, amount_usd: float, metadata=None):
    if not amount_usd or amount_usd <= 0:
        return None
    if not NEON_DSN or not HAS_PG:
        logger.info("[offline] revenue would-log %.2f USD from %s (%s)", amount_usd, source, revenue_type)
        return None
    try:
        with psycopg2.connect(NEON_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO monetization_ledger (source_agent, revenue_type, amount_usd, metadata) VALUES (%s,%s,%s,%s)",
                    (source, revenue_type, amount_usd, json.dumps(metadata or {})))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("revenue log failed (continuing): %s", e)
        return None
