import sys
import os

def test_import(module_name):
    print(f"Importing {module_name}...")
    try:
        __import__(module_name)
        print(f"Successfully imported {module_name}")
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")
        import traceback
        traceback.print_exc()

print("Current working directory:", os.getcwd())
sys.path.insert(0, os.getcwd())

test_import("app.core.config")
test_import("app.core.logging_config")
test_import("app.database")
test_import("app.models")
test_import("app.routers.auth")
test_import("app.routers.fixed_deposit")
test_import("app.routers.equity")
test_import("main")
print("Done.")
