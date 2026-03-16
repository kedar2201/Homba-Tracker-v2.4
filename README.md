# Homba Portfolio Tracker - Monorepo

This repository contains both the backend and frontend for the Homba Portfolio Tracker.

## Project Structure

- `backend/`: FastAPI application server.
  - `app/`: Core application logic (models, routers, services).
  - `main.py`: Entry point for the backend.
  - `requirements.txt`: Python dependencies.
  - `Dockerfile`: Deployment configuration for the backend.
- `frontend/`: Frontend application (Pre-built static files).
  - `dist/`: Built assets ready for serving.
  - `Dockerfile`: Nginx configuration to serve the frontend.
- `docker-compose.yml`: Orchestration for running both services.

## Deployment with Docker

To run the entire stack locally or on a server:

```bash
docker-compose up --build -d
```

The backend will be available at `http://localhost:8001` and the frontend at `http://localhost:3000`.

## Data Persistence

The backend database is stored in `backend/data/` (mapped to `/app/data/` in the container) to ensure persistence across restarts.

## Git Configuration

A comprehensive `.gitignore` has been added to the root to ensure only necessary files are uploaded to GitHub. This includes ignoring:
- Database files (`*.db`)
- Logs (`*.log`)
- Temporary zips (`*.zip`)
- Python cache (`__pycache__`)
- Migration/Debug scripts (unless explicitly tracked)
