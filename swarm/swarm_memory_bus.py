#!/usr/bin/env python3
"""
FRACTALMESH v10332.2 — Swarm Memory Bus (secrets-free port)
Reads NEON_DSN from env. If missing/unreachable, runs in OFFLINE/MOCK mode
so the bus can be smoke-tested without live credentials or a real Neon instance.
"""
import os, json, time, logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("SwarmMemoryBus")

NEON_DSN = os.getenv("NEON_DSN", "")
OFFLINE = not bool(NEON_DSN)


def _prometheus_stubs():
    """Return metric stubs when prometheus_client isn't installed."""
    class _Fake:
        def labels(self, **kw): return self
        def inc(self, n=1): pass
        def observe(self, v): pass
    class _FakeFactory:
        def __call__(self, *a, **k): return _Fake()
        def labels(self, **kw): return _Fake()
    return _FakeFactory(), _FakeFactory(), _FakeFactory(), _FakeFactory()


try:
    from prometheus_client import Counter, Histogram, start_http_server
    HAS_PROM = True
except Exception:
    Counter, Histogram, start_http_server, _unused = _prometheus_stubs()
    HAS_PROM = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PG = True
except Exception:
    psycopg2 = None
    HAS_PG = False


class SwarmMemoryBusOrchestrator:
    def __init__(self, dsn: Optional[str] = None, port: int = 8000):
        self.dsn = dsn or NEON_DSN
        self.mock = self._should_mock()
        self.conn = None
        if not self.mock:
            try:
                self.conn = psycopg2.connect(self.dsn)
                self.conn.autocommit = True
            except Exception as e:
                logger.warning("DB connect failed -> OFFLINE mode: %s", e)
                self.mock = True
        self.ingest_counter, self.ingest_latency, self.revenue_counter, self.revenue_latency = _prometheus_stubs()
        if HAS_PROM and not OFFLINE and not self.mock:
            try:
                start_http_server(port)
                logger.info("[+] Prometheus on :%s", port)
            except Exception as e:
                logger.warning("Prometheus start failed: %s", e)

    def _should_mock(self) -> bool:
        if OFFLINE:
            logger.info("NEON_DSN not set -> OFFLINE mock mode (no DB). Logs only.")
            return True
        if not HAS_PG:
            logger.warning("psycopg2 unavailable -> OFFLINE mock mode.")
            return True
        return False

    # ---- in-memory store used for offline/mock & for tests ----
    @property
    def memory(self):
        if not hasattr(self, "_mem"):
            self._mem = {"episodic": [], "semantic": [], "revenue": [], "gnss": []}
        return self._mem

    def _execute(self, sql, params=None, fetch=False):
        if self.mock:
            return None
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
            return cur.rowcount

    def batch_log_gnss(self, telemetry_list: List[Dict], tenant_id="default") -> List[str]:
        start = time.time()
        ids = []
        if self.mock:
            for t in telemetry_list:
                rec = {**t, "ts": time.time()}
                self.memory["gnss"].append(rec)
                ids.append("mock-" + str(len(self.memory["gnss"])))
            self.ingest_counter.labels(status="ok", tenant=tenant_id).inc(len(ids))
            self.ingest_latency.labels(op="batch", tenant=tenant_id).observe(time.time() - start)
            return ids
        with self.conn.cursor() as cur:
            for t in telemetry_list:
                cur.execute(
                    "INSERT INTO gnss_hot (agc_level, cn0_ratio, spoof_score, jam_score, metadata, tenant_id)"
                    " VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                    (t.get("agc"), t.get("cn0"), t.get("spoof", 0.0), t.get("jam", 0.0),
                     json.dumps(t.get("meta", {})), tenant_id))
                ids.append(str(cur.fetchone()[0]))
        self.ingest_counter.labels(status="ok", tenant=tenant_id).inc(len(ids))
        self.ingest_latency.labels(op="batch", tenant=tenant_id).observe(time.time() - start)
        return ids

    def log_episodic(self, event_type: str, payload: Dict, importance=0.0, tenant_id="default") -> str:
        if self.mock:
            rec = {"event_type": event_type, "payload": payload, "importance": importance, "tenant": tenant_id, "ts": time.time()}
            self.memory["episodic"].append(rec)
            return "mock-ep-" + str(len(self.memory["episodic"]))
        rows = self._execute(
            "INSERT INTO episodic_memory (event_type, payload, importance_score, tenant_id) VALUES (%s,%s,%s,%s) RETURNING id",
            (event_type, json.dumps(payload), importance, tenant_id), fetch=True)
        return str(rows[0]["id"])

    def log_semantic(self, content: str, embedding=None, metadata=None, tenant_id="default") -> str:
        if self.mock:
            self.memory["semantic"].append({"content": content, "metadata": metadata, "ts": time.time()})
            return "mock-sem-" + str(len(self.memory["semantic"]))
        rows = self._execute(
            "INSERT INTO semantic_memory (content, embedding, metadata, tenant_id) VALUES (%s,%s,%s,%s) RETURNING id",
            (content, embedding, json.dumps(metadata or {}), tenant_id), fetch=True)
        return str(rows[0]["id"])

    def log_revenue(self, source_agent: str, revenue_type: str, amount_usd: float, metadata=None, tenant_id="default") -> str:
        start = time.time()
        if self.mock:
            rec = {"source": source_agent, "type": revenue_type, "amount": amount_usd, "metadata": metadata, "ts": time.time()}
            self.memory["revenue"].append(rec)
            self.revenue_counter.labels(type=revenue_type, tenant=tenant_id).inc(1)
            self.revenue_latency.labels(tenant=tenant_id).observe(time.time() - start)
            return "mock-rev-" + str(len(self.memory["revenue"]))
        rows = self._execute(
            "INSERT INTO monetization_ledger (source_agent, revenue_type, amount_usd, metadata, tenant_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (source_agent, revenue_type, amount_usd, json.dumps(metadata or {}), tenant_id), fetch=True)
        self.revenue_counter.labels(type=revenue_type, tenant=tenant_id).inc(1)
        self.revenue_latency.labels(tenant=tenant_id).observe(time.time() - start)
        return str(rows[0]["id"])

    def get_recent_episodic(self, event_type=None, limit=100, tenant_id="default"):
        if self.mock:
            recs = [r for r in self.memory["episodic"] if not event_type or r.get("event_type") == event_type]
            return recs[-limit:]
        if event_type:
            return self._execute(
                "SELECT * FROM episodic_memory WHERE event_type=%s AND tenant_id=%s ORDER BY timestamp DESC LIMIT %s",
                (event_type, tenant_id, limit), fetch=True)
        return self._execute(
            "SELECT * FROM episodic_memory WHERE tenant_id=%s ORDER BY timestamp DESC LIMIT %s",
            (tenant_id, limit), fetch=True)

    def get_revenue_summary(self, tenant_id="default"):
        if self.mock:
            agg = {}
            for r in self.memory["revenue"]:
                k = (r["source"], r["type"])
                agg[k] = agg.get(k, 0.0) + r["amount"]
            return [{"source_agent": s, "revenue_type": t, "total": v} for (s, t), v in agg.items()]
        return self._execute(
            "SELECT source_agent, revenue_type, SUM(amount_usd) as total, COUNT(*) as count"
            " FROM monetization_ledger WHERE tenant_id=%s GROUP BY source_agent, revenue_type",
            (tenant_id,), fetch=True)

    def health(self):
        if self.mock:
            return {"status": "ok", "db": "offline-mock", "mode": "no-dsn-or-unreachable"}
        try:
            self._execute("SELECT 1")
            return {"status": "ok", "db": "connected"}
        except Exception as e:
            return {"status": "error", "db": str(e)}


def _self_test():
    """PEP-style self test for offline mode."""
    bus = SwarmMemoryBusOrchestrator(dsn="")
    assert bus.mock is True, "should run offline when no DSN"
    g = bus.batch_log_gnss([{"agc": 42.0, "cn0": 33.0}, {"agc": 50.0, "cn0": 31.0, "spoof": 0.1}])
    assert len(g) == 2, "2 gnss rows expected"
    e = bus.log_episodic("test_event", {"a": 1}, importance=0.9)
    assert e.startswith("mock-"), "mock episodic id expected"
    s = bus.log_semantic("hello world", metadata={"k": "v"})
    assert s.startswith("mock-"), "mock semantic id expected"
    r = bus.log_revenue("test_agent", "unit", 12.5)
    assert r.startswith("mock-"), "mock revenue id expected"
    assert len(bus.get_recent_episodic()) == 1
    rev = bus.get_revenue_summary()
    assert any(x["source_agent"] == "test_agent" for x in rev), "revenue summary expected"
    print("SELF_TEST: PASS  (offline mock stride)")
    print(json.dumps({"mode": "offline", "gnss_ids": g, "episodic": e, "revenue_summary": rev}, indent=2))


if __name__ == "__main__":
    if "--self-test" in os.sys.argv:
        _self_test()
    else:
        bus = SwarmMemoryBusOrchestrator()
        logger.info("[+] SwarmMemoryBus ready (%s)", "MOCK" if bus.mock else "LIVE")
        while True:
            time.sleep(60)
