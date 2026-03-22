import sys
import os
import uvicorn

# Ensure the backend directory is in the python path so Uvicorn can find 'main.py'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Change working directory so relative paths in the app stay correct
os.chdir(current_dir)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
