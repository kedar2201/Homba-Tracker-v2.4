import sys
import os

def test_module(module_name):
    print(f"Testing {module_name}...")
    try:
        __import__(module_name)
        print(f"Successfully imported {module_name}")
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")

sys.path.insert(0, os.getcwd())

test_module("sqlalchemy")
test_module("app.core.config")
test_module("app.database")
