import multiprocessing
import os

# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "fastapi_app"

# Timeout
timeout = 120
keepalive = 5
