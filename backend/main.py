# Portfolio Tracker Backend - Production Ready Version
import os
import sys
import logging
from contextlib import asynccontextmanager

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import global_exception_handler, validation_exception_handler
from app.database import engine, Base
from app import models
from app.routers import (
    auth, fixed_deposit, equity, mutual_fund, dashboard, 
    other_asset, market, reports, analytics, profitability, 
    rating, radar
)
from app.scheduler import start_scheduler, shutdown_scheduler

# Initialize logging
setup_logging()
logger = logging.getLogger("app.main")

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up application...")
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    # Shutdown logic
    logger.info("Shutting down application...")
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception Handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.middleware("http")
async def request_log_middleware(request: Request, call_next):

    """Log API requests for monitoring."""
    if request.url.path.startswith("/api/"):
        logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    if request.url.path.startswith("/api/"):
        logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
    
    return response

# Include Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=f"{api_v1_prefix}/auth")
app.include_router(fixed_deposit.router, prefix=f"{api_v1_prefix}/fixed-deposits")
app.include_router(equity.router, prefix=f"{api_v1_prefix}/equity")
app.include_router(mutual_fund.router, prefix=f"{api_v1_prefix}/mutual-funds")
app.include_router(other_asset.router, prefix=f"{api_v1_prefix}/other-assets")
app.include_router(dashboard.router, prefix=f"{api_v1_prefix}/dashboard")
app.include_router(market.router, prefix=f"{api_v1_prefix}/market")
app.include_router(reports.router, prefix=f"{api_v1_prefix}/reports")
app.include_router(analytics.router, prefix=f"{api_v1_prefix}/analytics")
app.include_router(profitability.router, prefix=f"{api_v1_prefix}/profitability")
app.include_router(rating.router, prefix=f"{api_v1_prefix}/rating")
app.include_router(radar.router, prefix=f"{api_v1_prefix}/radar")

# Serve Static Files / SPA
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_path):
    # Mount assets if they exist
    assets_path = os.path.join(static_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Ignore API paths
        if full_path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})
        
        # Check if requested file exists
        file_path = os.path.join(static_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to SPA index.html
        index_html = os.path.join(static_path, "index.html")
        if os.path.exists(index_html):
            return FileResponse(index_html)
        
        return JSONResponse(status_code=404, content={"detail": "Static content not found"})
else:
    @app.get("/")
    def read_root():
        return {"message": f"{settings.PROJECT_NAME} API Ready"}

@app.get("/health", tags=["Health"])
async def health_check():
    """Verify system health and database connectivity."""
    db_status = "unhealthy"
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"}
        )

    return {
        "status": "healthy",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

