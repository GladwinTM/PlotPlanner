#!/usr/bin/env bash
# Start (creating on first use) a throwaway local PostgreSQL for the test suite.
# It listens on 127.0.0.1:54329 only and is unrelated to Supabase.
#
#   backend/scripts/test_db.sh start|stop|status
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$HERE/.test-pg"
PORT="${TEST_DB_PORT:-54329}"
PG_BIN="${PG_BIN:-$(dirname "$(command -v pg_ctl || true)")}"

case "${1:-start}" in
  start)
    if [ ! -d "$DATA_DIR" ]; then
      "$PG_BIN/initdb" -D "$DATA_DIR" -U plotplanner --auth=trust -E UTF8 >/dev/null
    fi
    if ! "$PG_BIN/pg_ctl" -D "$DATA_DIR" status >/dev/null 2>&1; then
      "$PG_BIN/pg_ctl" -D "$DATA_DIR" -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=$DATA_DIR" \
        -l "$DATA_DIR/server.log" -w start >/dev/null
    fi
    "$PG_BIN/psql" -h 127.0.0.1 -p "$PORT" -U plotplanner -d postgres -tAc \
      "select 1 from pg_database where datname='plotplanner_test'" | grep -q 1 \
      || "$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U plotplanner plotplanner_test
    echo "test database ready: postgresql+psycopg://plotplanner@127.0.0.1:$PORT/plotplanner_test"
    ;;
  stop)
    "$PG_BIN/pg_ctl" -D "$DATA_DIR" -m fast stop
    ;;
  status)
    "$PG_BIN/pg_ctl" -D "$DATA_DIR" status
    ;;
  *)
    echo "usage: $0 start|stop|status" >&2
    exit 2
    ;;
esac
