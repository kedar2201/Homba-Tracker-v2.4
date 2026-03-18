"""
Database model for Stock Rating Summary.

One row per scrip. Stores the final composite score and component
subscores. The UI reads from this table only.

State machine:
  NEW → FETCHING → DERIVING → READY → RATED
  INVALID_CLASSIFICATION  (sector unknown → blocked)
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class DataState:
    NEW                    = "NEW"
    FETCHING               = "FETCHING"
    DERIVING               = "DERIVING"
    READY                  = "READY"
    RATED                  = "RATED"
    INVALID_CLASSIFICATION = "INVALID_CLASSIFICATION"

    # States where rating computation is allowed
    COMPUTABLE = {READY, RATED}


class StockRatingSummary(Base):
    """Computed rating summary – one row per scrip_code."""
    __tablename__ = "stock_rating_summary"

    scrip_code          = Column(String,  primary_key=True, index=True)
    sector_type         = Column(String,  default="NON_FINANCIAL")   # BANK | NBFC | NON_FINANCIAL

    # ── State machine ────────────────────────────────────────────────────────
    data_state          = Column(String,  default=DataState.NEW,
                                 nullable=False)
    # "RATED" means fully computed; anything else → UI shows "Computing…"

    # ── Rating scores ────────────────────────────────────────────────────────
    final_score         = Column(Float,   nullable=True)   # 0–100
    star_rating         = Column(Integer, nullable=True)   # 1–5
    trend_score         = Column(Float,   nullable=True)   # max 20
    valuation_score     = Column(Float,   nullable=True)   # max 25
    profitability_score = Column(Float,   nullable=True)   # max 35
    growth_score        = Column(Float,   nullable=True)   # max 20

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence_score    = Column(Float,   nullable=True)   # 0.0–1.0
    confidence_label    = Column(String,  nullable=True)   # Low/Medium/High/Full
    confidence_pts_have = Column(Integer, nullable=True)   # e.g. 7
    confidence_pts_max  = Column(Integer, nullable=True)   # e.g. 9

    # ── Trend confidence (separate — MA may be weak but not block) ───────────
    trend_confidence    = Column(String,  nullable=True)   # NORMAL | LOW

    # ── Audit / debug ────────────────────────────────────────────────────────
    fallbacks_applied   = Column(Text,    nullable=True)   # JSON list
    missing_fields      = Column(Text,    nullable=True)   # JSON list

    # ── Profitability snapshot (for display) ─────────────────────────────────
    roe_3y_avg          = Column(Float,   nullable=True)
    roce_3y_avg         = Column(Float,   nullable=True)

    calculated_fy       = Column(Integer, default=2025)
    last_updated        = Column(DateTime(timezone=True),
                                 server_default=func.now(),
                                 onupdate=func.now())
