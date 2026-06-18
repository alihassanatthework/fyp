#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Production-style server for LOCAL load testing (gunicorn + gevent).
#
#  Use this INSTEAD of `manage.py runserver` when running Locust — the
#  dev server is single-process and chokes above ~25 concurrent users.
#  gevent async workers let a few processes hold hundreds of connections.
#
#  Run from project root:
#     bash scripts/run_load_server.sh
#
#  Then in another terminal run the load test, e.g.:
#     locust --headless -u 150 -r 10 -t 2m --host http://localhost:8000 --html load_150.html
# ─────────────────────────────────────────────────────────────────
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "✗ venv not found"; exit 1
fi

# Raise the open-file-descriptor limit (macOS defaults to 256 — far too low
# for hundreds of concurrent sockets).
ulimit -n 10240 || true

echo "🚀 gunicorn + gevent on http://127.0.0.1:8000"
echo "   workers=4  worker-connections=1000  (≈ up to ~4000 concurrent sockets)"
echo "   open-file limit: $(ulimit -n)"

# All worker tuning + the critical gevent/psycopg2 monkey-patching lives in
# gunicorn_conf.py (post_fork). Without that patch the gevent workers hang on
# the first DB query.
exec gunicorn config.wsgi:application -c gunicorn_conf.py
