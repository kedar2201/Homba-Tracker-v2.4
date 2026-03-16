
import sys
import os
import logging
# Setup logging to console
logging.basicConfig(level=logging.INFO)

# Ensure 'app' is importable
sys.path.append(os.getcwd())

from app.services.nav_service import capture_all_users_nav

print("Triggering NAV capture on LIVE database...")
capture_all_users_nav()
print("Capture complete.")
