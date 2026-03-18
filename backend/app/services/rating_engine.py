"""
Stock Rating Engine — Data-First Rebuild
=========================================
Core principle: NEVER compute ratings on incomplete data.

Pipeline:
  1. check_readiness() -> DataReadinessResult
  2. If state != READY  -> update data_state, return early
  3. Compute bucket scores using resolved (possibly fallback) values
  4. Compute confidence score
  5. Store breakdown + confidence + audit trail

Scoring unchanged when data is present.
Missing data -> neutral score (not minimum-penalty).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.rating import StockRatingSummary, DataState
from ..models.market_data import PriceCache
from .rating_data_state import (
    check_readiness,
    DataReadinessResult,
    NEUTRAL_TREND_SCORE,
    NEUTRAL_PROFITABILITY_SCORE,
    NEUTRAL_GROWTH_SCORE,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  TREND SCORING  (max 20)
# ══════════════════════════════════════════════════════════════════════════════
def _score_trend(rd: DataReadinessResult) -> float:
    """
    Price vs 50/200 DMA.

    If MA data is missing (trend_confidence=LOW) -> neutral score (12/20).
    This avoids penalising a stock just because the MA hasn't been cached yet.
    """
    p    = rd.price
    ma50 = rd.ma50
    ma200 = rd.ma200

    if not p or p <= 0:
        return NEUTRAL_TREND_SCORE

    # Low confidence path — MA data absent
    if rd.trend_confidence == "LOW" or (not ma50 and not ma200):
        return NEUTRAL_TREND_SCORE  # 12/20 — neutral

    # Both MAs available
    if ma50 and ma200:
        if p > ma50 > ma200:
            return 20   # fully bullish
        if p > ma200 and p < ma50:
            return 14   # long-term bullish
        if p < ma50 and p > ma200:
            return 10   # short-term bullish
        return 4        # bearish (price below both)

    # Only MA200 available
    if ma200:
        return 14 if p > ma200 else 4

    # Only MA50 available
    if ma50:
        return 10 if p > ma50 else 4

    return NEUTRAL_TREND_SCORE


# ══════════════════════════════════════════════════════════════════════════════
# 2.  VALUATION SCORING  (max 25)
# ══════════════════════════════════════════════════════════════════════════════
def _score_valuation(
    rd: DataReadinessResult, pc: PriceCache
) -> tuple[float, float]:
    """
    Returns (valuation_score, growth_score).
    Both are derived from the same PE data.

    Part A — Forward PE compression (max 15):
      pe_2y < pe_1y < pe_current  -> 15 pts
      pe_1y < pe_current           -> 10 pts
      flat                         -> 6  pts
      expanding                    -> 2  pts

    Part B — Absolute trailing PE (max 10):
      < 15   -> 10 pts
      15–25  ->  7 pts
      25–40  ->  4 pts
      > 40   ->  0 pts

    Growth score (max 20) — also PE-based:
      Strong 2Y compression -> 20
      1Y compression        -> 14
      Flat                  ->  8
      Expanding             ->  2
    """
    pe   = rd.pe
    eps  = rd.eps
    feps = rd.forward_eps
    g    = rd.earnings_growth or 0.10
    price = rd.price

    if not pe or pe <= 0 or not price or price <= 0:
        return 2.0, NEUTRAL_GROWTH_SCORE  # can't score without PE

    # Derive forward PEs
    pe_1y: Optional[float] = None
    pe_2y: Optional[float] = None

    if feps and feps > 0:
        pe_1y = price / feps
        if eps and eps > 0:
            eps_2y = eps * ((1 + g) ** 2)
            pe_2y = price / eps_2y if eps_2y > 0 else None
    elif eps and eps > 0 and g:
        eps_1y = eps * (1 + g)
        eps_2y = eps * ((1 + g) ** 2)
        pe_1y = price / eps_1y if eps_1y > 0 else None
        pe_2y = price / eps_2y if eps_2y > 0 else None

    # ── Part A: Forward PE trend ──────────────────────────────────────────────
    if pe_1y and pe_2y:
        if pe_2y < pe_1y < pe:
            score_a = 15
        elif pe_1y < pe:
            score_a = 10
        elif abs(pe_1y - pe) < 1:
            score_a = 6
        else:
            score_a = 2
    elif pe_1y:
        if pe_1y < pe:
            score_a = 10
        elif abs(pe_1y - pe) < 1:
            score_a = 6
        else:
            score_a = 2
    else:
        score_a = 6  # neutral — can't compute forward PE at all

    # ── Part B: Absolute PE ───────────────────────────────────────────────────
    if pe < 15:
        score_b = 10
    elif pe <= 25:
        score_b = 7
    elif pe <= 40:
        score_b = 4
    else:
        score_b = 0

    val_score = min(score_a + score_b, 25)

    # ── Growth score ──────────────────────────────────────────────────────────
    if pe_1y and pe_2y:
        if pe_2y < pe_1y < pe:
            growth = 20
        elif pe_1y < pe and abs(pe_2y - pe_1y) < 1:
            growth = 14
        elif abs(pe_1y - pe) < 1:
            growth = 8
        else:
            growth = 2
    elif pe_1y:
        if pe_1y < pe:
            growth = 14
        elif abs(pe_1y - pe) < 1:
            growth = 8
        else:
            growth = 2
    else:
        growth = NEUTRAL_GROWTH_SCORE

    return val_score, min(growth, 20)


def _score_growth_bank(rd: DataReadinessResult) -> float:
    """
    Bank Growth Scoring (max 20) based on Forward PE compression.
    Rules:
    - pe_2y < pe_1y         -> 20 pts (Future growth)
    - pe_1y < current_pe    -> 15 pts (Immediate growth)
    - pe_missing            -> 10 pts (Neutral)
    - pe_increasing         -> 5  pts (Warning)
    """
    pe = rd.pe
    price = rd.price
    feps = rd.forward_eps
    g = rd.earnings_growth or 0.10

    if not pe or pe <= 0 or not price or price <= 0:
        return 10.0  # Missing current data -> neutral

    # Derive forward PEs
    pe_1y = price / feps if feps and feps > 0 else None
    
    # 2Y Forward PE is always a derivation in this system
    eps_2y = rd.eps * ((1 + g) ** 2) if rd.eps else None
    pe_2y = price / eps_2y if (price and eps_2y and eps_2y > 0) else None

    if pe_2y and pe_1y and pe_2y < pe_1y:
        return 20.0
    if pe_1y and pe_1y < pe:
        return 15.0
    if not pe_1y:
        return 10.0
    
    return 5.0  # pe_increasing


# ══════════════════════════════════════════════════════════════════════════════
# 3.  PROFITABILITY SCORING  (max 35)
# ══════════════════════════════════════════════════════════════════════════════
def _score_profitability_non_bank(rd: DataReadinessResult) -> float:
    """
    Non-financial scoring (max 35):
      ROE 3Y   (max 10): >18% -> 10 | ≥14% -> 7  | <14% -> 4
      ROCE 3Y  (max 9):  >16% -> 9  | ≥12% -> 6  | <12% -> 3
      ROE curr (max 8):  >20% -> 8  | ≥15% -> 6  | <15% -> 3  (proxy = 3Y avg)
      ROCE curr(max 8):  >18% -> 8  | ≥14% -> 6  | <14% -> 3  (proxy = 3Y avg)

    If fallback was applied -> 0.5 weight on that sub-score.
    If completely neutral needed -> NEUTRAL_PROFITABILITY_SCORE.
    """
    roe_3y  = rd.roe_3y
    roce_3y = rd.roce_3y

    if roe_3y is None and roce_3y is None:
        return NEUTRAL_PROFITABILITY_SCORE  # 18/35

    # ─ ROE 3Y ─────────────────────────────────────────────────────────────────
    if roe_3y is None:
        roe_3y_score = 4
    elif roe_3y > 18:
        roe_3y_score = 10
    elif roe_3y >= 14:
        roe_3y_score = 7
    else:
        roe_3y_score = 4

    # ─ ROCE 3Y ────────────────────────────────────────────────────────────────
    if roce_3y is None:
        roce_3y_score = 3
    elif roce_3y > 16:
        roce_3y_score = 9
    elif roce_3y >= 12:
        roce_3y_score = 6
    else:
        roce_3y_score = 3

    # ─ Current ROE proxy (= 3Y avg until we have dedicated column) ────────────
    roe_curr = roe_3y
    if roe_curr is None:
        roe_curr_score = 3
    elif roe_curr > 20:
        roe_curr_score = 8
    elif roe_curr >= 15:
        roe_curr_score = 6
    else:
        roe_curr_score = 3

    # ─ Current ROCE proxy ─────────────────────────────────────────────────────
    roce_curr = roce_3y
    if roce_curr is None:
        roce_curr_score = 3
    elif roce_curr > 18:
        roce_curr_score = 8
    elif roce_curr >= 14:
        roce_curr_score = 6
    else:
        roce_curr_score = 3

    # Apply half-weight if fallback was used
    weight = 0.5 if rd.roe_is_fallback else 1.0
    raw = (roe_3y_score + roce_3y_score + roe_curr_score + roce_curr_score)
    return min(round(raw * weight + NEUTRAL_PROFITABILITY_SCORE * (1 - weight), 1), 35)


def _score_profitability_bank(rd: DataReadinessResult) -> float:
    """
    Bank / NBFC scoring — ROE only (max 35).
    Rules:
    - ROE >= 18% -> 35 pts
    - ROE >= 15% -> 28 pts
    - ROE >= 12% -> 22 pts
    - ROE >= 9%  -> 15 pts
    - ROE < 9%   -> 8 pts
    """
    roe = rd.roe_3y
    if roe is None:
        return 18.0 # Neutral fallback

    if roe >= 18: return 35.0
    if roe >= 15: return 28.0
    if roe >= 12: return 22.0
    if roe >= 9:  return 15.0
    return 8.0


# ══════════════════════════════════════════════════════════════════════════════
# 4.  STAR RATING CONVERTER
# ══════════════════════════════════════════════════════════════════════════════
def _to_stars(score: float) -> int:
    """
    Scale:
    - 80+ -> 5 Stars
    - 65+ -> 4 Stars
    - 50+ -> 3 Stars
    - 35+ -> 2 Stars
    - <35 -> 1 Star
    """
    if score >= 80: return 5
    if score >= 65: return 4
    if score >= 50: return 3
    if score >= 35: return 2
    return 1


# ══════════════════════════════════════════════════════════════════════════════
# 5.  MAIN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════
def compute_and_store_rating(db: Session, scrip_code: str) -> dict:
    """
    Full pipeline: check readiness → score → store.
    Returns a dict with the result or a reason for skipping.
    """
    code = scrip_code.upper()

    # ── Step 1: Readiness check ───────────────────────────────────────────────
    rd = check_readiness(code, db)

    # Mark or update the rating row with current state
    row = db.query(StockRatingSummary).filter(
              StockRatingSummary.scrip_code == code).first()
    if row is None:
        row = StockRatingSummary(scrip_code=code)
        db.add(row)

    row.sector_type      = rd.sector
    row.data_state       = rd.state
    row.missing_fields   = rd.missing_json
    row.fallbacks_applied = rd.fallbacks_json
    row.trend_confidence = rd.trend_confidence

    if rd.state != DataState.READY:
        db.commit()
        logger.info(
            f"[Rating] {code}: skipped — state={rd.state}, "
            f"missing={rd.mandatory_missing}"
        )
        return {
            "scrip_code": code,
            "state":      rd.state,
            "skipped":    True,
            "reason":     f"mandatory missing: {rd.mandatory_missing}",
        }

    # ── Step 2: Score ─────────────────────────────────────────────────────────
    pc = db.query(PriceCache).filter(PriceCache.symbol == code).first()

    trend_score = _score_trend(rd)
    val_score, base_growth_score = _score_valuation(rd, pc)

    if rd.sector == "BANK":
        prof_score = _score_profitability_bank(rd)
        growth_score = _score_growth_bank(rd)
    else:
        prof_score = _score_profitability_non_bank(rd)
        growth_score = base_growth_score

    final = round(trend_score + val_score + prof_score + growth_score, 2)
    stars  = _to_stars(final)

    # ── Step 3: Confidence ────────────────────────────────────────────────────
    row.confidence_score    = rd.confidence_score
    row.confidence_label    = rd.confidence_label
    row.confidence_pts_have = rd.pts_have
    row.confidence_pts_max  = rd.pts_max

    # ── Step 4: Persist ───────────────────────────────────────────────────────
    row.final_score         = final
    row.star_rating         = stars
    row.trend_score         = trend_score
    row.valuation_score     = val_score
    row.profitability_score = prof_score
    row.growth_score        = growth_score
    row.data_state          = DataState.RATED
    row.roe_3y_avg          = rd.roe_3y
    row.roce_3y_avg         = rd.roce_3y
    row.last_updated        = datetime.utcnow()

    db.commit()

    logger.info(
        f"[Rating] {code}: score={final} stars={stars} "
        f"confidence={rd.confidence_label}({rd.pts_have}/{rd.pts_max}) "
        f"fallbacks={rd.fallbacks_applied}"
    )

    return {
        "scrip_code":       code,
        "state":            DataState.RATED,
        "final_score":      final,
        "star_rating":      stars,
        "trend_score":      trend_score,
        "valuation_score":  val_score,
        "profitability_score": prof_score,
        "growth_score":     growth_score,
        "confidence_score": rd.confidence_score,
        "confidence_label": rd.confidence_label,
        "fallbacks_applied": rd.fallbacks_applied,
    }


def get_all_ratings(db: Session) -> dict:
    """Return a dict of scrip_code → rating object for the UI."""
    rows = db.query(StockRatingSummary).all()
    return {
        r.scrip_code: {
            "star_rating":      r.star_rating,
            "final_score":      r.final_score,
            "trend_score":      r.trend_score,
            "valuation_score":  r.valuation_score,
            "profitability_score": r.profitability_score,
            "growth_score":     r.growth_score,
            "data_state":       r.data_state or DataState.NEW,
            "confidence_score": r.confidence_score,
            "confidence_label": r.confidence_label,
            "confidence_pts_have": r.confidence_pts_have,
            "confidence_pts_max":  r.confidence_pts_max,
            "trend_confidence": r.trend_confidence,
            "fallbacks_applied": json.loads(r.fallbacks_applied or "[]"),
            "missing_fields":    json.loads(r.missing_fields or "[]"),
            "sector_type":      r.sector_type,
            "last_updated":     r.last_updated.isoformat() if r.last_updated else None,
        }
        for r in rows
    }


def get_rating(db: Session, scrip_code: str) -> Optional[dict]:
    """Return single scrip rating or None."""
    all_ratings = get_all_ratings(db)
    return all_ratings.get(scrip_code.upper())
