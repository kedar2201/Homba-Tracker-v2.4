# Portfolio Tracker Backend - Azure Deployment Version
import os
import sys
# THIS TELLS PYTHON WHERE THE 'APP' FOLDER IS
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routers import auth, fixed_deposit, equity, mutual_fund, dashboard, other_asset, market, reports, analytics, profitability, rating, radar
from app.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title="Financial Portfolio Tracker")

@app.on_event("startup")
def startup_event():
    # Only create tables if we are not in a test/dev environment where they are handled differently
    models.Base.metadata.create_all(bind=engine)
    start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import logging
logging.basicConfig(filename="api_requests.log", level=logging.INFO)

@app.middleware("http")
async def log_requests(request, call_next):
    body = await request.body()
    # Log only for relevant paths to avoid spamming
    if "/api/" in request.url.path:
        logging.info(f"Method: {request.method} Path: {request.url.path} Body: {body.decode()}")
    
    # Put body back so FastAPI can read it
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive
    
    response = await call_next(request)
    if "/api/" in request.url.path:
        logging.info(f"Status: {response.status_code}")
    return response

# Include Routers with /api prefix
app.include_router(auth.router, prefix="/api/auth")
app.include_router(fixed_deposit.router, prefix="/api/fixed-deposits")
app.include_router(equity.router, prefix="/api/equity")
app.include_router(mutual_fund.router, prefix="/api/mutual-funds")
app.include_router(other_asset.router, prefix="/api/other-assets")
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(market.router, prefix="/api/market")
app.include_router(reports.router, prefix="/api/reports")
app.include_router(analytics.router, prefix="/api/analytics")
app.include_router(profitability.router, prefix="/api/profitability")
app.include_router(rating.router, prefix="/api/rating")
app.include_router(radar.router, prefix="/api/radar")

# Serve Static Files
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # If the path starts with api, it should have been caught by the routers above
        if full_path.startswith("api"):
            return {"detail": "Not Found"}
        
        # Check if the file exists in static folder (like favicon.ico, etc)
        file_path = os.path.join(static_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Otherwise serve index.html for React routing
        return FileResponse(os.path.join(static_path, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Financial Portfolio Tracker API Ready (Static files not found)"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": "cloud"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
