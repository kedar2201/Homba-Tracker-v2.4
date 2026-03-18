"""
Rating Data State Service
=========================
Evaluates a scrip's data readiness before rating computation.

State machine:
  NEW -> FETCHING -> DERIVING -> READY -> RATED
                             └─ INVALID_CLASSIFICATION (unknown sector)

Usage:
    from app.services.rating_data_state import check_readiness, DataReadinessResult
    result = check_readiness("RELIANCE", db)
    if result.state == "READY":
        compute_rating(...)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from ..models.market_data import PriceCache
from ..models.profitability_metrics import StockProfitabilitySummary
from ..models.rating import DataState

logger = logging.getLogger(__name__)

# ── Sector constants ──────────────────────────────────────────────────────────
BANK_KEYWORDS = [
    "BANK", "NBFC", "HOUSING FINANCE", "BHFL", "BAJAJ FIN",
    "FINANCIAL SERVICES", "GRUH", "LICHSGFIN",
    "INSURANCE", "LIFE", "GENERAL INS"
]
EXPLICIT_NBFC = {
    "BAJAJFIN", "BAJFINANCE", "LICHSGFIN", "MUTHOOTFIN",
    "PFC", "REC", "IRFC", "HDFC", "GRUH",
}

# ── Sector medians (fallback when profitability data absent) ──────────────────
SECTOR_MEDIAN_ROE  = 14.0   # %  — conservative median for large-cap India
SECTOR_MEDIAN_ROCE = 12.0   # %

# ── Neutral scores (used when data is genuinely unavailable) ──────────────────
# These put a stock in the middle, not at the bottom, when data is missing.
NEUTRAL_TREND_SCORE         = 12.0  # out of 20  (vs penalty 4)
NEUTRAL_PROFITABILITY_SCORE = 18.0  # out of 35  (midpoint)
NEUTRAL_GROWTH_SCORE        = 10.0  # out of 20


# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass
class DataReadinessResult:
    state: str                    # DataState.*
    sector: str                   # BANK | NON_FINANCIAL

    # Mandatory gaps that BLOCK rating
    mandatory_missing: list[str] = field(default_factory=list)

    # Resolved field values (including fallbacks)
    price:          Optional[float] = None
    ma50:           Optional[float] = None
    ma200:          Optional[float] = None
    eps:            Optional[float] = None
    pe:             Optional[float] = None
    forward_eps:    Optional[float] = None
    earnings_growth: Optional[float] = None
    roe_3y:         Optional[float] = None
    roce_3y:        Optional[float] = None

    # Flags
    trend_confidence: str = "NORMAL"  # NORMAL | LOW
    roe_is_fallback:  bool = False
    roce_is_fallback: bool = False

    # Audit
    fallbacks_applied: list[str] = field(default_factory=list)
    missing_optional:  list[str] = field(default_factory=list)

    # Confidence
    pts_have: int = 0
    pts_max:  int = 9

    @property
    def confidence_score(self) -> float:
        return round(self.pts_have / self.pts_max, 3) if self.pts_max else 0.0

    @property
    def confidence_label(self) -> str:
        pct = self.confidence_score
        if pct >= 1.0:  return "Full"
        if pct >= 0.75: return "High"
        if pct >= 0.50: return "Medium"
        return "Low"

    @property
    def fallbacks_json(self) -> str:
        return json.dumps(self.fallbacks_applied)

    @property
    def missing_json(self) -> str:
        return json.dumps(self.mandatory_missing + self.missing_optional)


# ── Sector detection ──────────────────────────────────────────────────────────
def _detect_sector(
    scrip_code: str,
    prof_row: Optional[StockProfitabilitySummary],
) -> str:
    """
    Returns "BANK" or "NON_FINANCIAL".
    Defaults to "NON_FINANCIAL" if no banking indicators are found.
    """
    code_upper = scrip_code.upper()

    # 1. Explicit NBFC list
    if code_upper in EXPLICIT_NBFC:
        return "BANK"

    # 2. Profitability service flag (most reliable)
    if prof_row is not None:
        return "BANK" if prof_row.is_bank else "NON_FINANCIAL"

    # 3. Keyword match on scrip code
    for kw in BANK_KEYWORDS:
        if kw in code_upper:
            return "BANK"

    # 4. Default to Non-Financial (Industrial/Service)
    return "NON_FINANCIAL"


# ── Main readiness check ──────────────────────────────────────────────────────
def check_readiness(scrip_code: str, db: Session) -> DataReadinessResult:
    """
    Evaluate data readiness for a scrip and return a DataReadinessResult.

    This is the single entry point before any rating computation.
    """
    code = scrip_code.upper()

    pc   = db.query(PriceCache).filter(PriceCache.symbol == code).first()
    prof = db.query(StockProfitabilitySummary).filter(
               StockProfitabilitySummary.scrip_code == code).first()

    # ── Sector classification ─────────────────────────────────────────────────
    sector = _detect_sector(code, prof)
    if sector is None:
        return DataReadinessResult(
            state=DataState.INVALID_CLASSIFICATION,
            sector="UNKNOWN",
            mandatory_missing=["sector_classification"],
        )

    is_bank = (sector == "BANK")
    pts_max = 8 if is_bank else 9  # banks don't need ROCE

    result = DataReadinessResult(state=DataState.READY, sector=sector, pts_max=pts_max)

    # ── Price data checks ─────────────────────────────────────────────────────
    # --- 1. CORE MARKET DATA (MANDATORY) ---
    if not pc:
        logger.warning(f"[{code}] No PriceCache entry found. State: NEW")
        result.state = DataState.NEW
        result.mandatory_missing.append("market_data_presence")
        return result

    # Check for Yahoo Symbol Mapping
    if not pc.yahoo_symbol:
        logger.warning(f"[{code}] Missing yahoo_symbol mapping. State: FETCHING")
        result.state = DataState.FETCHING
        result.mandatory_missing.append("yahoo_symbol_mapping")
        return result

    # Price — mandatory
    if pc.price and pc.price > 0:
        result.price = pc.price
        result.pts_have += 1
    else:
        result.mandatory_missing.append("price")

    # MA50 — optional (neutral score if missing, not block)
    if pc.ma50 and pc.ma50 > 0:
        result.ma50 = pc.ma50
        result.pts_have += 1
    else:
        result.missing_optional.append("ma50")
        result.trend_confidence = "LOW"
        result.fallbacks_applied.append("ma50 missing -> trend_confidence=LOW, neutral trend score applied")

    # MA200 — optional (same — neutral score)
    if pc.ma200 and pc.ma200 > 0:
        result.ma200 = pc.ma200
        result.pts_have += 1
    else:
        result.missing_optional.append("ma200")
        result.trend_confidence = "LOW"
        if "ma200 missing" not in " ".join(result.fallbacks_applied):
            result.fallbacks_applied.append("ma200 missing -> trend_confidence=LOW, neutral trend score applied")

    # EPS — mandatory
    if pc.eps and pc.eps != 0:
        result.eps = pc.eps
        result.pts_have += 1
    else:
        result.mandatory_missing.append("eps")

    # PE — mandatory
    if pc.pe and pc.pe > 0:
        result.pe = pc.pe
        result.pts_have += 1
    else:
        result.mandatory_missing.append("pe")

    # ── Forward / growth data (optional) ─────────────────────────────────────
    # Forward EPS — fallback chain: forward_eps → eps*(1+g) → None
    if pc.forward_eps and pc.forward_eps != 0:
        result.forward_eps = pc.forward_eps
        result.pts_have += 1
    else:
        result.missing_optional.append("forward_eps")
        # Derive from EPS + growth rate
        g = _resolve_growth_rate(pc, result)
        if result.eps:
            derived = result.eps * (1 + g)
            result.forward_eps = derived
            result.fallbacks_applied.append(
                f"forward_eps derived from eps×(1+{g:.2f}) = {derived:.2f}"
            )
        # partial credit for derived forward EPS
        result.pts_have += 0.5

    # Earnings growth — resolve chain
    _resolve_growth_rate(pc, result)  # fills result.earnings_growth + updates pts_have

    # ── Profitability data checks ─────────────────────────────────────────────
    _resolve_roe(prof, result)
    if not is_bank:
        _resolve_roce(prof, result)

    # ── Final state determination ─────────────────────────────────────────────
    if result.mandatory_missing:
        # Has some data but mandatory fields missing → FETCHING
        result.state = DataState.FETCHING
    else:
        result.state = DataState.READY

    return result


# ── ROE fallback chain ────────────────────────────────────────────────────────
def _resolve_roe(
    prof: Optional[StockProfitabilitySummary],
    result: DataReadinessResult,
) -> None:
    """Resolve ROE via fallback chain; never block on missing ROE."""
    if prof and prof.roe_3y_avg and prof.roe_3y_avg > 0:
        result.roe_3y  = prof.roe_3y_avg
        result.pts_have += 1
        return

    # Fallback 1: current ROE (same table, might be None)
    # (we don't have a separate current_roe column yet, so skip)

    # Fallback 2: sector median
    result.roe_3y        = SECTOR_MEDIAN_ROE
    result.roe_is_fallback = True
    result.missing_optional.append("roe_3y_avg")
    result.fallbacks_applied.append(
        f"roe_3y_avg missing -> using sector median {SECTOR_MEDIAN_ROE}%"
    )
    # Give partial credit
    result.pts_have += 0.5


# ── ROCE fallback chain ───────────────────────────────────────────────────────
def _resolve_roce(
    prof: Optional[StockProfitabilitySummary],
    result: DataReadinessResult,
) -> None:
    """Resolve ROCE via fallback chain (only called for non-financial)."""
    if prof and prof.roce_3y_avg and prof.roce_3y_avg > 0:
        result.roce_3y  = prof.roce_3y_avg
        result.pts_have += 1
        return

    result.roce_3y         = SECTOR_MEDIAN_ROCE
    result.roce_is_fallback = True
    result.missing_optional.append("roce_3y_avg")
    result.fallbacks_applied.append(
        f"roce_3y_avg missing -> using sector median {SECTOR_MEDIAN_ROCE}%"
    )
    result.pts_have += 0.5


# ── Growth rate resolver ──────────────────────────────────────────────────────
def _resolve_growth_rate(
    pc: Optional[PriceCache],
    result: DataReadinessResult,
) -> float:
    """
    Resolve earnings growth rate via priority chain.
    Priority: Yahoo earnings_growth > user eps_growth > default 10%
    Returns the resolved rate (decimal, e.g. 0.10 for 10%).
    """
    if pc is None:
        return 0.10

    # 1. Yahoo earnings_growth (stored as decimal in DB, e.g. 0.15)
    if pc.earnings_growth and abs(pc.earnings_growth) > 0:
        g = pc.earnings_growth
        if result.earnings_growth is None:
            result.pts_have += 1
        result.earnings_growth = g
        return g

    # 2. User-set eps_growth (stored as %, convert to decimal)
    if pc.eps_growth and abs(pc.eps_growth) > 0:
        g = pc.eps_growth / 100.0
        if result.earnings_growth is None:
            result.pts_have += 0.5
        result.earnings_growth = g
        result.fallbacks_applied.append(
            f"earnings_growth missing -> using user eps_growth {pc.eps_growth}%"
        )
        return g

    # 3. Default 10%
    result.earnings_growth = 0.10
    result.missing_optional.append("earnings_growth")
    result.fallbacks_applied.append(
        "earnings_growth missing -> using sector default 10%"
    )
    return 0.10
