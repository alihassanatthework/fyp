"""
Gunicorn config for local load testing with gevent async workers.

The critical part is making psycopg2 (a C extension that blocks the gevent
event loop) cooperate with gevent. Without patch_psycopg() the gevent worker
hangs on the first database query. These patches must run in each worker
*before* it handles requests — `post_fork` is the correct hook.
"""

bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
timeout = 120
loglevel = "warning"
accesslog = "-"


def post_fork(server, worker):
    # Make sockets cooperative, then make psycopg2 cooperative too.
    from gevent import monkey
    monkey.patch_all()
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
