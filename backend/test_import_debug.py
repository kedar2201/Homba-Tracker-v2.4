import sys
import os
sys.path.insert(0, os.path.abspath("."))
print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Search Path: {sys.path}")
print("Starting import test...")
try:
    import main
    print("Successfully imported FastAPI app")
    print(f"Routes: {[route.path for route in main.app.routes]}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
