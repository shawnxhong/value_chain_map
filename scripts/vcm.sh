#!/usr/bin/env bash
#
# VCM local deploy WITHOUT Docker Compose.
#
#   Postgres  -> a single `docker run` container (no compose networking / image builds)
#   Backend   -> native `uv run uvicorn` (uses your host network, so LLM/EDGAR calls work)
#   Frontend  -> native `npm run dev` (Vite proxies /api -> backend)
#
# Usage:
#   scripts/vcm.sh up            # postgres + migrate + backend + frontend
#   scripts/vcm.sh seed [args]   # run the pipeline seed (e.g. seed --no-edgar --max-chunks 4)
#   scripts/vcm.sh status        # what's running + URLs
#   scripts/vcm.sh logs backend|frontend|db
#   scripts/vcm.sh restart backend|frontend
#   scripts/vcm.sh down [--db]   # stop backend+frontend (and postgres with --db)
#   scripts/vcm.sh db up|down|destroy|psql
#   scripts/vcm.sh backend up|down|migrate
#   scripts/vcm.sh frontend up|down
#
# Config overrides (env): VCM_PG_IMAGE, VCM_PG_PORT, VCM_BACKEND_PORT, VCM_FRONTEND_PORT.
# LLM keys + provider selection are read from infra/.env.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$ROOT/.run"
ENV_FILE="$ROOT/infra/.env"
mkdir -p "$RUN_DIR"

# uv installs to ~/.local/bin, which isn't always on a minimal PATH.
export PATH="$HOME/.local/bin:$PATH"

# Run as yourself, NOT as root: the backend/frontend run under your user (your uv, npm, venv),
# and the script elevates to `sudo docker` on its own just for Postgres. Running the whole thing
# under sudo breaks uv/npm PATH and leaves root-owned files behind.
if [ "$(id -u)" -eq 0 ]; then
  printf '\033[1;31m[vcm]\033[0m %s\n' \
    "don't run this with sudo — it calls 'sudo docker' itself for Postgres and runs the app as your user." >&2
  printf '\033[1;31m[vcm]\033[0m %s\n' "re-run WITHOUT sudo:  ./scripts/vcm.sh ${*:-up}" >&2
  exit 1
fi

PG_CONTAINER="${VCM_PG_CONTAINER:-vcm-postgres}"
PG_IMAGE="${VCM_PG_IMAGE:-pgvector/pgvector:pg16}"   # matches infra/docker-compose.yml; postgres:16 also works for Phase 0
PG_VOLUME="${VCM_PG_VOLUME:-vcm-pgdata}"
PG_PORT="${VCM_PG_PORT:-5432}"
BACKEND_PORT="${VCM_BACKEND_PORT:-8000}"
FRONTEND_PORT="${VCM_FRONTEND_PORT:-5173}"
DB_URL="postgresql+psycopg://vcm:vcm@localhost:${PG_PORT}/vcm"

# This host's SOCKS proxy (ALL_PROXY) breaks httpx/npm (no socksio); strip it and keep the
# HTTP proxy. Prefix every network-touching command with this.
NOSOCKS=(env -u ALL_PROXY -u all_proxy)

log()  { printf '\033[1;34m[vcm]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[vcm]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[vcm]\033[0m %s\n' "$*" >&2; exit 1; }

# ---- docker (auto-detect sudo; snap docker on this host needs it) ----
DOCKER=()
setup_docker() {
  [ ${#DOCKER[@]} -gt 0 ] && return
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
  elif sudo -n docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    DOCKER=(sudo docker)
    warn "docker needs sudo on this host — you may be prompted for your password"
  fi
}
dk() { setup_docker; "${DOCKER[@]}" "$@"; }

# ---- postgres ----
pg_run() {  # (re)create the container; data lives in the named volume, so this is non-destructive
  dk run -d --name "$PG_CONTAINER" \
    -e POSTGRES_USER=vcm -e POSTGRES_PASSWORD=vcm -e POSTGRES_DB=vcm \
    -p "127.0.0.1:${PG_PORT}:5432" \
    -v "${PG_VOLUME}:/var/lib/postgresql/data" \
    "$PG_IMAGE" >/dev/null
}
pg_ready_inside() {  # postgres accepting connections *inside* the container
  for _ in $(seq 1 "${1:-60}"); do
    dk exec "$PG_CONTAINER" pg_isready -U vcm -d vcm >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}
host_port_open() {  # the published port actually forwards to the host (what the backend needs)
  for _ in $(seq 1 "${1:-15}"); do
    (exec 3<>"/dev/tcp/127.0.0.1/${PG_PORT}") >/dev/null 2>&1 && { exec 3>&- 3<&-; return 0; }
    sleep 1
  done
  return 1
}
db_up() {
  if dk ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
    log "postgres container already running"
  elif dk ps -a --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
    log "starting existing postgres container"
    dk start "$PG_CONTAINER" >/dev/null
  else
    log "creating postgres container ($PG_IMAGE) — pulls the image on first run"
    pg_run
  fi
  log "waiting for postgres..."
  pg_ready_inside 60 || die "postgres did not start inside the container in 60s — check: scripts/vcm.sh logs db"
  # pg_isready passing inside the container does NOT guarantee the host port forwards
  # (docker sometimes drops the published port on a stop/start) — verify and self-heal.
  if ! host_port_open 15; then
    warn "host port $PG_PORT not forwarding (stale published port) — recreating the container (data volume kept)"
    dk rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
    pg_run
    pg_ready_inside 60 || die "postgres did not start after recreate — check: scripts/vcm.sh logs db"
    host_port_open 15 || die "postgres still unreachable on 127.0.0.1:$PG_PORT.
     Something else may be holding $PG_PORT (check:  ss -ltnp | grep $PG_PORT  — e.g. a Compose postgres).
     Stop it, or run everything on another port:  VCM_PG_PORT=5433 ./scripts/vcm.sh up"
  fi
  log "postgres ready on localhost:${PG_PORT}"
}
db_down()    { log "stopping postgres"; dk stop "$PG_CONTAINER" >/dev/null 2>&1 || true; }
db_destroy() { dk rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true; dk volume rm "$PG_VOLUME" >/dev/null 2>&1 || true; log "postgres container + volume removed"; }
db_psql()    { dk exec -it "$PG_CONTAINER" psql -U vcm -d vcm; }

# ---- backend (native uvicorn) ----
proc_running() { local f="$RUN_DIR/$1.pid"; [ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null; }
port_in_use()  { [ -n "$(ss -ltnH "sport = :$1" 2>/dev/null)" ]; }

backend_migrate() {
  log "running migrations (alembic upgrade head)"
  ( cd "$ROOT/backend" && VCM_DATABASE_URL="$DB_URL" "${NOSOCKS[@]}" uv run alembic upgrade head )
}
backend_up() {
  [ -f "$ENV_FILE" ] || die "missing $ENV_FILE (LLM keys + provider); create it from the compose defaults"
  log "syncing backend deps (uv sync)"
  ( cd "$ROOT/backend" && "${NOSOCKS[@]}" uv sync )
  backend_migrate
  if proc_running backend; then log "backend already running (pid $(cat "$RUN_DIR/backend.pid"))"; return; fi
  if port_in_use "$BACKEND_PORT"; then
    die "port $BACKEND_PORT is already in use (often a leftover Docker Compose backend container). Free it — e.g.:
       sudo docker compose -f infra/docker-compose.yml down
       sudo docker ps --filter publish=$BACKEND_PORT -q | xargs -r sudo docker stop
     ...or run on another port:  VCM_BACKEND_PORT=8001 ./scripts/vcm.sh up"
  fi
  log "starting backend on :$BACKEND_PORT"
  ( cd "$ROOT/backend"
    set -a; . "$ENV_FILE"; set +a                       # export ANTHROPIC/OPENAI/DEEPSEEK keys + VCM_* provider
    VCM_DATABASE_URL="$DB_URL" \
      setsid nohup "${NOSOCKS[@]}" uv run uvicorn vcm.main:app \
        --host 0.0.0.0 --port "$BACKEND_PORT" \
        >"$RUN_DIR/backend.log" 2>&1 </dev/null &
    echo $! >"$RUN_DIR/backend.pid" )
  for _ in $(seq 1 40); do
    if "${NOSOCKS[@]}" curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
      log "backend healthy: http://localhost:${BACKEND_PORT}/api/health"
      return
    fi
    sleep 0.5
  done
  warn "backend did not report healthy yet — check: scripts/vcm.sh logs backend"
}

# ---- frontend (native vite dev) ----
frontend_up() {
  log "installing frontend deps (npm install)"
  ( cd "$ROOT/frontend" && "${NOSOCKS[@]}" npm install --no-fund --no-audit >/dev/null )
  if proc_running frontend; then log "frontend already running (pid $(cat "$RUN_DIR/frontend.pid"))"; return; fi
  log "starting frontend on :$FRONTEND_PORT"
  ( cd "$ROOT/frontend"
    VITE_API_PROXY="http://localhost:${BACKEND_PORT}" \
      setsid nohup "${NOSOCKS[@]}" npm run dev -- --port "$FRONTEND_PORT" \
        >"$RUN_DIR/frontend.log" 2>&1 </dev/null &
    echo $! >"$RUN_DIR/frontend.pid" )
  sleep 2
  log "frontend: $(frontend_url)  (log: scripts/vcm.sh logs frontend)"
}
frontend_url() { grep -oE 'http://localhost:[0-9]+' "$RUN_DIR/frontend.log" 2>/dev/null | head -1 || echo "http://localhost:${FRONTEND_PORT}"; }

# ---- process control ----
stop_proc() {
  local name="$1" f="$RUN_DIR/$1.pid"
  if proc_running "$name"; then
    local pid; pid="$(cat "$f")"
    log "stopping $name (pgid $pid)"
    kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  else
    log "$name not running"
  fi
  rm -f "$f"
}

# ---- seed ----
seed() {
  [ -f "$ENV_FILE" ] || die "missing $ENV_FILE"
  proc_running backend || warn "backend not running; seed writes straight to postgres regardless"
  log "running: python -m vcm.seed $*"
  ( cd "$ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    VCM_DATABASE_URL="$DB_URL" "${NOSOCKS[@]}" uv run python -m vcm.seed "$@" )
}

# ---- aggregate ----
up() {
  db_up
  backend_up
  frontend_up
  echo
  log "up. open the UI:  $(frontend_url)"
  log "seed data with:   scripts/vcm.sh seed          (add --no-edgar to skip the SEC 10-K fetch)"
}
down() {
  stop_proc frontend
  stop_proc backend
  [ "${1:-}" = "--db" ] && db_down || true
}
status() {
  if dk ps --format '{{.Names}}' 2>/dev/null | grep -qx "$PG_CONTAINER"; then
    printf 'postgres : running   (localhost:%s, image %s)\n' "$PG_PORT" "$PG_IMAGE"
  else printf 'postgres : stopped\n'; fi
  if proc_running backend; then
    printf 'backend  : running   pid %s   http://localhost:%s/api/health\n' "$(cat "$RUN_DIR/backend.pid")" "$BACKEND_PORT"
  else printf 'backend  : stopped\n'; fi
  if proc_running frontend; then
    printf 'frontend : running   pid %s   %s\n' "$(cat "$RUN_DIR/frontend.pid")" "$(frontend_url)"
  else printf 'frontend : stopped\n'; fi
}
logs() {
  case "${1:-}" in
    backend)  tail -f "$RUN_DIR/backend.log" ;;
    frontend) tail -f "$RUN_DIR/frontend.log" ;;
    db)       dk logs -f "$PG_CONTAINER" ;;
    *) die "usage: scripts/vcm.sh logs backend|frontend|db" ;;
  esac
}

# ---- dispatch ----
cmd="${1:-}"; shift || true
case "$cmd" in
  up)       up ;;
  down)     down "${1:-}" ;;
  restart)  case "${1:-}" in
              backend)  stop_proc backend; backend_up ;;
              frontend) stop_proc frontend; frontend_up ;;
              *) die "usage: scripts/vcm.sh restart backend|frontend" ;;
            esac ;;
  status)   status ;;
  logs)     logs "${1:-}" ;;
  seed)     seed "$@" ;;
  db)       case "${1:-}" in
              up) db_up ;; down) db_down ;; destroy) db_destroy ;; psql) db_psql ;;
              *) die "usage: scripts/vcm.sh db up|down|destroy|psql" ;;
            esac ;;
  backend)  case "${1:-}" in
              up) db_up; backend_up ;; down) stop_proc backend ;; migrate) backend_migrate ;;
              *) die "usage: scripts/vcm.sh backend up|down|migrate" ;;
            esac ;;
  frontend) case "${1:-}" in
              up) frontend_up ;; down) stop_proc frontend ;;
              *) die "usage: scripts/vcm.sh frontend up|down" ;;
            esac ;;
  ""|-h|--help|help)
    awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}" ;;
  *) die "unknown command: $cmd (try: scripts/vcm.sh help)" ;;
esac
