#!/usr/bin/env python3
"""FractalMesh -> Rork Max ingestion mapper (v10324.1).

Transforms graph/telemetry payloads into flat relational analytics.
Rule contract:
  mesh_id       -> transaction_id  (prefix RM-)
  timestamp     -> ingested_at     (ISO 8601 UTC)
  cluster_status-> system_health_flag (true iff "healthy")
  nodes[].node_id            -> entities[].rork_entity_id
  nodes[].telemetry.signal_strength -> entities[].performance_metric (float)
  nodes[].telemetry.latency_ms      -> entities[].is_optimal (latency_ms < 50)

Usage:
  python3 tools/mapper.py < input.json               # stdout -> output.json
  python3 tools/mapper.py --in file.json --out out.json
  python3 tools/mapper.py --self-test
"""
import json
import sys
from datetime import datetime, timezone

SLA_LATENCY_MS = 50


def transform_fractal_to_rork(fractal_payload: dict) -> dict:
    rork_payload = {
        "transaction_id": f"RM-{fractal_payload.get('mesh_id', 'UNKNOWN')}",
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "system_health_flag": fractal_payload.get("cluster_status") == "healthy",
        "entities": [],
    }
    for node in fractal_payload.get("nodes", []):
        telemetry = node.get("telemetry", {})
        rork_payload["entities"].append({
            "rork_entity_id": str(node.get("node_id", "")).replace("-node", ""),
            "performance_metric": float(telemetry.get("signal_strength", 0.0)),
            "is_optimal": int(telemetry.get("latency_ms", 999)) < SLA_LATENCY_MS,
        })
    return rork_payload


def _sample():
    return {
        "mesh_id": "abc123",
        "timestamp": "2026-08-14T03:00:00Z",
        "cluster_status": "healthy",
        "nodes": [
            {"node_id": "n1-node", "telemetry": {"signal_strength": 0.87, "latency_ms": 30}},
            {"node_id": "n2-node", "telemetry": {"signal_strength": 0.54, "latency_ms": 72}},
        ],
    }


def self_test():
    out = transform_fractal_to_rork(_sample())
    assert out["transaction_id"] == "RM-abc123", out
    assert out["system_health_flag"] is True
    assert out["entities"][0]["rork_entity_id"] == "n1"
    assert out["entities"][0]["is_optimal"] is True
    assert out["entities"][1]["is_optimal"] is False
    assert isinstance(out["entities"][0]["performance_metric"], float)
    print("SELF_TEST: PASS")
    print(json.dumps(out, indent=2))


def main():
    if "--self-test" in sys.argv:
        self_test()
        return 0
    infile = outfile = None
    if "--in" in sys.argv:
        infile = sys.argv[sys.argv.index("--in") + 1]
    if "--out" in sys.argv:
        outfile = sys.argv[sys.argv.index("--out") + 1]
    data = json.load(open(infile)) if infile else json.load(sys.stdin)
    result = transform_fractal_to_rork(data)
    if outfile:
        json.dump(result, open(outfile, "w"), indent=2)
        print(f"mapped -> {outfile}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
