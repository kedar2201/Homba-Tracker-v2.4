"""
API Router for Stock Profitability Metrics (ROE & ROCE).

Endpoints:
  GET  /api/profitability/summary               → all cached summaries (bulk)
  GET  /api/profitability/summary/{scrip_code}  → one scrip's cached summary
  POST /api/profitability/compute/{scrip_code}  → force-recompute for one scrip
  POST /api/profitability/compute-all           → recompute for all user's active equities
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.user import User
from ..auth.auth import get_current_user
from ..services import profitability_service as ps

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Profitability"])


@router.get("/summary")
def get_all_summaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return cached 3-year ROE/ROCE summaries for all scrips.
    The UI calls this once on equity page load."""
    return ps.get_all_summaries(db)


@router.get("/summary/{scrip_code}")
def get_scrip_summary(
    scrip_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return cached summary for a single scrip (or 404 if not yet computed)."""
    data = ps.get_summary(db, scrip_code.upper())
    if not data:
        raise HTTPException(status_code=404, detail="No profitability data yet. Use /compute to fetch.")
    return data


@router.post("/compute/{scrip_code}")
def compute_scrip(
    scrip_code: str,
    ticker: Optional[str] = None,
    is_bank: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch from Yahoo Finance and compute ROE/ROCE for one scrip.
    If ticker is not provided, it defaults to '<SCRIP_CODE>.NS'.
    """
    code = scrip_code.upper()
    yf_ticker = ticker or f"{code}.NS"
    result = ps.compute_and_store_profitability(db, code, yf_ticker, is_bank)
    return result


def _compute_all_job(db: Session, equities):
    """Background job: compute profitability for all unique scrips."""
    seen = set()
    for eq in equities:
        code = (eq.get("symbol") or "").upper()
        if not code or code in seen:
            continue
        seen.add(code)
        exchange = eq.get("exchange", "NSE")
        suffix = ".BO" if exchange == "BSE" else ".NS"
        ticker = f"{code}{suffix}"
        try:
            ps.compute_and_store_profitability(db, code, ticker)
        except Exception as e:
            logger.error(f"[Profitability] Failed for {code}: {e}")


@router.post("/compute-all")
async def compute_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a background compute for all active equities belonging to the user.
    Returns immediately; computation runs in the background.
    """
    from ..models.equity import Equity, EquityStatus

    equities = (
        db.query(Equity)
        .filter(
            Equity.user_id == current_user.id,
            (Equity.status == EquityStatus.ACTIVE) | (Equity.status == None),
        )
        .all()
    )

    eq_list = [
        {"symbol": eq.symbol, "exchange": str(eq.exchange.value if hasattr(eq.exchange, "value") else eq.exchange)}
        for eq in equities
    ]

    unique_count = len({e["symbol"].upper() for e in eq_list if e["symbol"]})

    background_tasks.add_task(_compute_all_job, db, eq_list)

    return {
        "status": "started",
        "message": f"Computing ROE/ROCE for {unique_count} unique scrips in the background. Refresh in ~30s.",
    }
