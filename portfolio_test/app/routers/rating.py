"""
API Router for Stock Rating Engine.

Endpoints:
  GET  /api/rating/all             → bulk dict of scrip_code → rating
  GET  /api/rating/{scrip_code}    → cached rating (or 404)
  POST /api/rating/compute/{code}  → compute & store rating for one scrip
  POST /api/rating/compute-all     → compute all active equities (background)
"""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth import get_current_user
from ..models.user import User
from ..services import rating_engine as re_svc

logger = logging.getLogger(__name__)

# Resolve path to backend root (two levels up from this file)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router = APIRouter(tags=["Rating"])


@router.get("/download/pdf", include_in_schema=False)
def download_requirements_pdf():
    """Download rating data-requirements PDF (no auth needed)."""
    path = os.path.join(_BACKEND_DIR, "rating_data_requirements.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF not found. Run generate_rating_data_requirements.py first.")
    return FileResponse(path, media_type="application/pdf",
                        filename="rating_data_requirements.pdf")


@router.get("/download/excel", include_in_schema=False)
def download_requirements_excel():
    """Download rating data-requirements Excel (no auth needed)."""
    path = os.path.join(_BACKEND_DIR, "rating_data_requirements.xlsx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Excel not found. Run generate_rating_data_requirements.py first.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="rating_data_requirements.xlsx"
    )


@router.get("/download/audit-pdf", include_in_schema=False)
def download_audit_pdf():
    """Download per-scrip data audit PDF (no auth needed)."""
    path = os.path.join(_BACKEND_DIR, "scrip_data_audit.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audit PDF not found. Run generate_scrip_data_audit.py first.")
    return FileResponse(path, media_type="application/pdf", filename="scrip_data_audit.pdf")


@router.get("/download/audit-excel", include_in_schema=False)
def download_audit_excel():
    """Download per-scrip data audit Excel (no auth needed)."""
    path = os.path.join(_BACKEND_DIR, "scrip_data_audit.xlsx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audit Excel not found. Run generate_scrip_data_audit.py first.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="scrip_data_audit.xlsx"
    )


@router.get("/all")
def get_all_ratings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return cached ratings for all scrips – called once on equity page load."""
    return re_svc.get_all_ratings(db)


@router.get("/{scrip_code}")
def get_rating(
    scrip_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return cached rating for one scrip (or 404 if not yet computed)."""
    data = re_svc.get_rating(db, scrip_code.upper())
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Rating not computed yet. Use /compute to trigger.",
        )
    return data


@router.post("/compute/{scrip_code}")
def compute_rating(
    scrip_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Force-compute (or recompute) rating for one scrip and cache the result."""
    result = re_svc.compute_and_store_rating(db, scrip_code.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


def _compute_all_job(db: Session, codes: list):
    """Background job: compute ratings for all unique scrips."""
    for code in codes:
        try:
            re_svc.compute_and_store_rating(db, code)
        except Exception as e:
            logger.error(f"[Rating] Failed for {code}: {e}")


@router.post("/compute-all")
async def compute_all_ratings(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger background computation of ratings for all active equities.
    Returns immediately while computation runs in the background.
    """
    from ..scheduler import wrapper_compute_all_ratings
    background_tasks.add_task(wrapper_compute_all_ratings)

    return {
        "status": "started",
        "message": "Computing ratings for all scrips in background. Check back in a minute.",
    }


@router.get("/audit", include_in_schema=False)
def get_rating_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch bulk data availability and fallback audit for all scrips."""
    all_data = re_svc.get_all_ratings(db)
    # Filter or transform if needed, but for now /all is already detailed
    return all_data
