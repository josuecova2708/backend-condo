import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 65

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Load application code before the worker processes are forked
preload_app = True

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'smart_condo_gunicorn'

# Server mechanics
daemon = False
pidfile = None
user = None
group = None

# SSL is handled by the reverse proxy (Coolify/Railway/Nginx), not gunicorn
keyfile = None
certfile = None

# Railway specific optimizations
def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    server.log.info("Server shutting down")