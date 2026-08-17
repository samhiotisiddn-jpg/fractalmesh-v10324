#!/usr/bin/env bash
# ───────────────────────────────────────────────────────────────────
# FRACTALMESH v10332.2 SWARM DEPLOY — secrets-free launcher
# All credentials MUST come from an environment file. Nothing is
# hardcoded in this repo. No secrets are written by this script.
# ───────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${FRACTALMESH_BASE:-$REPO}"
LOGS="${FRACTALMESH_LOGS:-$BASE/logs}"
PIDS="$BASE/pids"
mkdir -p "$BASE" "$LOGS" "$PIDS"
cd "$REPO"

# Load secrets from an optional, git-ignored env file.
if [ -f "$BASE/.env" ]; then
  echo "[*] Loading secrets from $BASE/.env"
  set -a; . "$BASE/.env"; set +a
else
  echo "[!] No $BASE/.env found. Agents will run in OFFLINE/MOCK mode (no live creds)."
  echo "    Copy .env.example to $BASE/.env and fill with YOUR values on the HOST ONLY."
fi

echo "[+] FRACTALMESH v10332.2 deploy starting (repo=$REPO)"

# ── deps (best effort; system python may already have these) ──────
PY="${PYTHON:-python3}"
$PY -m pip install --quiet --upgrade pip 2>/dev/null || true
$PY -m pip install --quiet requests websocket-client flask flask-sock psycopg2-binary tenacity prometheus_client 2>/dev/null || true

# Pick which processes to run (default: all). Set AGENTS env to override.
run_agent() {
  local name="$1"
  if [ -n "${AGENTS:-}" ]; then
    case " $AGENTS " in *" $name "*) ;; *) echo "  skip $name"; return ;; esac
  fi
  nohup "$PY" "$BASE/swarm/$name" > "$LOGS/$name.log" 2>&1 &
  echo $! > "$PIDS/$name.pid"
  echo "  started $name (pid $!)"
}

echo "[*] Launching swarm..."
run_agent swarm_memory_bus.py
run_agent master_orchestrator.py
run_agent trading_agent.py
run_agent nft_agent.py
run_agent commerce_agent.py
run_agent social_agent.py
run_agent scrape_agent.py
run_agent aiscrape_agent.py
run_agent static_server.py

sleep 2
echo ""
echo "--- STATUS -------------------------------------------------"
for f in "$PIDS"/*.pid; do
  [ -e "$f" ] || continue
  n="$(basename "$f" .pid)"
  pid="$(cat "$f")"
  if kill -0 "$pid" 2>/dev/null; then st="RUNNING"; else st="DEAD"; fi
  printf "  %-28s pid=%-7s %s\n" "$n" "$pid" "$st"
done
echo "------------------------------------------------------------"
echo "  Logs:        $LOGS"
echo "  Master API:  http://0.0.0.0:${MASTER_PORT:-7784}"
echo "  Dashboard:   http://0.0.0.0:${STATIC_PORT:-7790}/dashboard.html"
echo "  OMNI:        http://0.0.0.0:${STATIC_PORT:-7790}/omni.html"
echo ""
echo "[+] Deployment complete. Monitor with: tail -f $LOGS/*.log"
