#!/usr/bin/env bash
# FRACTALMESH v10332.2 — stop the swarm cleanly from pids/
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PIDS="$(pwd)/pids"
[ -d "$PIDS" ] || { echo "no pids dir"; exit 0; }
for f in "$PIDS"/*.pid; do
  [ -e "$f" ] || continue
  pid="$(cat "$f")"
  kill "$pid" 2>/dev/null && echo "stopped $(basename "$f" .pid) ($pid)" || echo "not running $(basename "$f" .pid)"
  rm -f "$f"
done
echo "[+] Swarm stopped."
