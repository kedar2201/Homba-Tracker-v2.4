import logging
import sys
from .config import settings
import os

def setup_logging():
    log_dir = settings.LOG_DIR
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Avoid crashing background threads if stdout is closed during shutdown.
    # In production, logging exceptions should never take down the process.
    logging.raiseExceptions = settings.ENVIRONMENT != "production"

    # Fallback logging if file writing fails (common in production/Windows locks)
    try:
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8")
        handlers = [file_handler]
    except Exception as e:
        print(f"WARNING: Could not initialize file logging: {e}")
        handlers = []

    if getattr(sys.stdout, "closed", False) is False:
        handlers.insert(0, logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger("app")
