@echo off
cd /d L:\apps\portfolio\backend
C:\Users\kedar\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
