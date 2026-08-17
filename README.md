# FRACTALMESH — Omega Titan v10332.2

Multi-agent monetization + memory swarm for Samuel James Hiotis (ABN 56 628 117 363, Sole Trader).
This repo is the **secrets-free** deployment base: all credentials are read from a local, git-ignored
`.env` on the host — never committed.

> Security: any secret pasted into chat/scripts is considered exposed. Rotate wallet keys, Stripe live,
> and exchange API keys. Real keys belong ONLY in `/host/.env`, never in this repo.

## Layout

```
public/           Static product site (index.html)
web/              Dashboard + OMNISIMULATOR (served by static_server)
swarm/            Agent swarm (env-driven, offline-safe)
  swarm_memory_bus.py     Postgres Unified-Memory-Bus + Prometheus metrics
  master_orchestrator.py  Flask :7784 — CORS, WebSocket, /api/revenue|gnss|episodic|agents, /health
  trading_agent.py        Pionex + KuCoin + CoinGecko -> episodic memory
  nft_agent.py            Alchemy + OpenSea + WAX RAM
  commerce_agent.py       Stripe + Printful
  social_agent.py         Telegram + Dev.to
  scrape_agent.py         Firecrawl + Crawlbase
  aiscrape_agent.py       Summarize queued scrapes (OpenRouter/Groq) -> semantic memory
  static_server.py        :7790 serves web/ + public/
  deploy.sh / stop.sh     Start/stop the swarm from .env
tools/mapper.py     FractalMesh -> RorkMax field mapper (self-test: PASS)
worker/build.sh     Portable AI-Horde worker build (CUDA/OpenBLAS auto)
```

## Quickstart (secrets-free / offline)

```bash
pip install requests flask flask-sock psycopg2-binary prometheus_client tenacity

# all agents run in OFFLINE/MOCK mode (no NEON_DSN)
python3 swarm/swarm_memory_bus.py --self-test   # SELF_TEST: PASS
python3 swarm/master_orchestrator.py            # :7784 -> /health returns offline-mock
./swarm/deploy.sh                               # launch swarm (offline until .env filled)
```

Endpoints (online mode): `:7784 /health /api/revenue /api/gnss /api/episodic /api/agents /ws`
Static: `:7790 /dashboard.html /omni.html`, Prometheus `:8000`.

## Go live

1. `cp .env.example .env` on the host and fill with freshly-issued secrets only.
2. `./swarm/deploy.sh` — sources `.env`, launches agents, writes pids/ + logs/.
3. Apply the Neon schema: see `SWARM_SCHEMA` note (vector + RLS tables) in `swarm_memory_bus.py` usage / docs.
4. Monitor: `tail -f logs/*.log`, `./swarm/stop.sh` to halt.

## Verify

`python3 tools/mapper.py --self-test` → PASS · `bash -n swarm/*.sh` · `python3 -m py_compile swarm/*.py`
