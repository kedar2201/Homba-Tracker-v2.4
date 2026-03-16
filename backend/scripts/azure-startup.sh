#!/bin/bash
# Move to the backend directory where main.py is
cd /home/site/wwwroot/

# Start the application using gunicorn
# -w 4: 4 worker processes
# -k uvicorn.workers.UvicornWorker: Use uvicorn workers for FastAPI
# --bind 0.0.0.0:8000: Listen on port 8000 (Azure's standard)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app
