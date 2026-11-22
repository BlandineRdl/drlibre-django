#!/bin/sh
# Runs the Locust load test on its own compose project and volume, then removes them; `--keep` leaves it up.
set -eu
cd "$(dirname "$0")/.."

export COMPOSE_PROJECT_NAME=drlibre-load
export WEB_PORT=18000 POSTGRES_PORT=15432 REDIS_PORT=16379 MAILPIT_SMTP_PORT=11025 MAILPIT_PORT=18025
export NETWORK_HOURLY_LIMIT=100000 APP_IMAGE_TAG=load

keep=false
if [ "${1:-}" = "--keep" ]; then keep=true; shift; fi
teardown() { if [ "$keep" = false ]; then docker compose down -v --remove-orphans; fi; }
trap teardown EXIT

docker compose up -d --build --wait
docker compose exec -T web python -m scripts.seed --size load
# Fresh bulk rows leave planner statistics stale until autovacuum runs.
docker compose exec -T postgres sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c ANALYZE'
# Signed-in roles use the seed's password, read from the seed itself.
LOAD_PASSWORD=$(docker compose exec -T web python -c 'from scripts.seed import DEMO_PASSWORD; print(DEMO_PASSWORD)' | tail -n 1)
# An empty password would lock the admin after repeated runs.
[ -n "$LOAD_PASSWORD" ] || { echo "LOAD_PASSWORD empty: cannot read scripts.seed.DEMO_PASSWORD" >&2; exit 1; }
export LOAD_PASSWORD
MAILPIT_URL="http://localhost:$MAILPIT_PORT" uv run locust -f loadtests/locustfile.py \
  --headless -u 20 -r 5 -t 3m --host "http://localhost:$WEB_PORT" "$@"
