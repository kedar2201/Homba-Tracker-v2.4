"""
Profitability Service — Fetches, Computes, and Caches ROE & ROCE.

Logic:
  1. Fetch Income Statement + Balance Sheet from Yahoo Finance (annual)
  2. Compute ROE and ROCE per fiscal year (FY2023, FY2024, FY2025)
  3. Store year-wise values in stock_profitability_metrics
  4. Compute 3-year averages and store in stock_profitability_summary

Bank Detection Logic:
  - If EBIT and Current Liabilities are both absent from the balance sheet,
    we classify the scrip as a Bank/NBFC (ROCE is not calculated).
  - User can also explicitly pass is_bank=True.
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..models.profitability_metrics import (
    StockProfitabilityMetric,
    StockProfitabilitySummary,
    DataSource,
)

logger = logging.getLogger(__name__)

# FYs to target (Indian FY ends in March, so year ending March 2023 = FY2023)
TARGET_FISCAL_YEARS = [2023, 2024, 2025]

# Keywords that strongly indicate a Bank/NBFC via scrip name
BANK_KEYWORDS = [
    "BANK", "NBFC", "FINANCIAL SERVICES", "HOUSING FINANCE", "BAJAJ FIN",
    "CHOLAFIN", "M&MFIN", "MUTHOOTFIN", "SHRIRAMFIN", "SUNDARMFIN",
    "BANDHANBNK", "AXISBANK", "HDFCBANK", "ICICIBANK", "IDBI", "INDIANB",
    "KOTAKBANK", "INSURANCE", "LIFE", "GENERAL INS"
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_col_for_year(df: pd.DataFrame, target_year: int) -> Optional[object]:
    """Return the DataFrame column (Timestamp) whose .year == target_year."""
    for col in df.columns:
        try:
            if col.year == target_year:
                return col
        except Exception:
            pass
    return None


def _safe_val(df: pd.DataFrame, key: str, col) -> Optional[float]:
    """Safely extract a float from a DataFrame cell."""
    if key not in df.index or col is None:
        return None
    v = df.loc[key, col]
    if pd.isna(v):
        return None
    return float(v)


def _detect_is_bank(scrip_code: str, inc: pd.DataFrame, bs: pd.DataFrame) -> bool:
    """
    Return True if the scrip is likely a Bank/NBFC.
    Heuristic: if EBIT is completely absent AND Current Liabilities absent → Bank.
    Also check scrip_code name.
    """
    name_upper = scrip_code.upper()
    if any(kw in name_upper for kw in BANK_KEYWORDS):
        return True

    # Check if EBIT / Operating Income exists in at least one FY column
    has_ebit = "EBIT" in inc.index or "Operating Income" in inc.index
    has_curr_liab = "Current Liabilities" in bs.index or "Total Current Liabilities" in bs.index

    # Banks typically lack both
    if not has_ebit and not has_curr_liab:
        return True

    return False


# ─── Core Computation ─────────────────────────────────────────────────────────

def compute_and_store_profitability(
    db: Session,
    scrip_code: str,
    ticker_symbol: str,
    is_bank: Optional[bool] = None,  # None → auto-detect
) -> dict:
    """
    Fetch raw financials, compute ROE & ROCE, persist, and return summary dict.
    Returns a dict with: roe_3y_avg, roce_3y_avg, is_bank, financials_incomplete.
    """
    logger.info(f"[Profitability] Computing for {scrip_code} ({ticker_symbol})")

    try:
        t = yf.Ticker(ticker_symbol)
        inc = t.income_stmt     # annual income statement
        bs  = t.balance_sheet   # annual balance sheet
    except Exception as e:
        logger.error(f"[Profitability] yfinance error for {ticker_symbol}: {e}")
        return _store_incomplete(db, scrip_code, ticker_symbol)

    if inc is None or inc.empty or bs is None or bs.empty:
        logger.warning(f"[Profitability] Empty statements for {ticker_symbol}")
        return _store_incomplete(db, scrip_code, ticker_symbol)

    # Auto-detect bank if not overridden
    if is_bank is None:
        is_bank = _detect_is_bank(scrip_code, inc, bs)

    roe_by_year: dict = {}
    roce_by_year: dict = {}
    missing_years = []

    for yr in TARGET_FISCAL_YEARS:
        inc_col = _get_col_for_year(inc, yr)
        bs_col  = _get_col_for_year(bs,  yr)

        if inc_col is None or bs_col is None:
            logger.warning(f"[Profitability] {scrip_code} FY{yr}: missing statement column")
            missing_years.append(yr)
            roe_by_year[yr]  = None
            roce_by_year[yr] = None
            continue

        # ── ROE ──────────────────────────────────────────────────────────────
        net_income = _safe_val(inc, "Net Income", inc_col)
        equity = (
            _safe_val(bs, "Stockholders Equity", bs_col)
            or _safe_val(bs, "Common Stock Equity", bs_col)
            or _safe_val(bs, "Total Equity Gross Minority Interest", bs_col)
        )

        if net_income is None or equity is None:
            roe_by_year[yr] = None
        elif equity <= 0:
            logger.info(f"[Profitability] {scrip_code} FY{yr}: negative equity → ROE=NULL")
            roe_by_year[yr] = None
        else:
            roe_by_year[yr] = round((net_income / equity) * 100, 4)

        # ── ROCE (skip for banks) ─────────────────────────────────────────────
        if is_bank:
            roce_by_year[yr] = None
            continue

        ebit = (
            _safe_val(inc, "EBIT", inc_col)
            or _safe_val(inc, "Operating Income", inc_col)
        )
        total_assets = _safe_val(bs, "Total Assets", bs_col)
        curr_liab = (
            _safe_val(bs, "Current Liabilities", bs_col)
            or _safe_val(bs, "Total Current Liabilities", bs_col)
        )

        if ebit is None or total_assets is None or curr_liab is None:
            roce_by_year[yr] = None
        else:
            cap_employed = total_assets - curr_liab
            if cap_employed <= 0:
                logger.info(f"[Profitability] {scrip_code} FY{yr}: CE≤0 → ROCE=NULL")
                roce_by_year[yr] = None
            else:
                roce_by_year[yr] = round((ebit / cap_employed) * 100, 4)

    # ── Persist year-wise rows ────────────────────────────────────────────────
    for yr in TARGET_FISCAL_YEARS:
        _upsert_metric(db, scrip_code, ticker_symbol, yr, is_bank,
                       roe_by_year.get(yr), roce_by_year.get(yr))

    # ── Compute 3-year averages ────────────────────────────────────────────────
    valid_roes  = [v for v in roe_by_year.values()  if v is not None]
    valid_roces = [v for v in roce_by_year.values() if v is not None]

    roe_3y  = round(sum(valid_roes)  / len(valid_roes),  2) if valid_roes  else None
    roce_3y = round(sum(valid_roces) / len(valid_roces), 2) if valid_roces else None
    financials_incomplete = len(missing_years) > 0

    # ── Persist summary ──────────────────────────────────────────────────────
    _upsert_summary(db, scrip_code, ticker_symbol, is_bank,
                    roe_3y, roce_3y, financials_incomplete)

    return {
        "scrip_code": scrip_code,
        "is_bank": is_bank,
        "roe_3y_avg": roe_3y,
        "roce_3y_avg": roce_3y,
        "financials_incomplete": financials_incomplete,
        "roe_by_year": roe_by_year,
        "roce_by_year": roce_by_year,
    }


def get_summary(db: Session, scrip_code: str) -> Optional[dict]:
    """Return the cached summary for a scrip or None if not computed yet."""
    row = db.query(StockProfitabilitySummary).filter(
        StockProfitabilitySummary.scrip_code == scrip_code
    ).first()
    if not row:
        return None
    return {
        "scrip_code":   row.scrip_code,
        "is_bank":      row.is_bank,
        "roe_3y_avg":   row.roe_3y_avg,
        "roce_3y_avg":  row.roce_3y_avg,
        "valid_till_fy": row.valid_till_fy,
        "financials_incomplete": row.financials_incomplete,
        "last_refresh": row.last_refresh.isoformat() if row.last_refresh else None,
    }


def get_all_summaries(db: Session) -> dict:
    """Return a dict of scrip_code → summary for all cached scrips."""
    rows = db.query(StockProfitabilitySummary).all()
    result = {}
    for row in rows:
        result[row.scrip_code] = {
            "is_bank":      row.is_bank,
            "roe_3y_avg":   row.roe_3y_avg,
            "roce_3y_avg":  row.roce_3y_avg,
            "financials_incomplete": row.financials_incomplete,
        }
    return result


# ─── DB Helpers ──────────────────────────────────────────────────────────────

def _upsert_metric(db, scrip_code, ticker, yr, is_bank, roe, roce):
    row = db.query(StockProfitabilityMetric).filter(
        StockProfitabilityMetric.scrip_code == scrip_code,
        StockProfitabilityMetric.fiscal_year == yr,
    ).first()
    if row:
        row.roe = roe
        row.roce = roce
        row.is_bank = is_bank
        row.calculated_at = datetime.utcnow()
    else:
        row = StockProfitabilityMetric(
            scrip_code=scrip_code, ticker=ticker,
            fiscal_year=yr, roe=roe, roce=roce,
            is_bank=is_bank, data_source=DataSource.Yahoo,
        )
        db.add(row)
    db.commit()


def _upsert_summary(db, scrip_code, ticker, is_bank, roe_3y, roce_3y, incomplete):
    row = db.query(StockProfitabilitySummary).filter(
        StockProfitabilitySummary.scrip_code == scrip_code
    ).first()
    if row:
        row.ticker = ticker
        row.is_bank = is_bank
        row.roe_3y_avg = roe_3y
        row.roce_3y_avg = roce_3y
        row.valid_till_fy = max(TARGET_FISCAL_YEARS)
        row.financials_incomplete = incomplete
    else:
        row = StockProfitabilitySummary(
            scrip_code=scrip_code, ticker=ticker,
            is_bank=is_bank, roe_3y_avg=roe_3y, roce_3y_avg=roce_3y,
            valid_till_fy=max(TARGET_FISCAL_YEARS),
            financials_incomplete=incomplete,
        )
        db.add(row)
    db.commit()


def _store_incomplete(db, scrip_code, ticker):
    _upsert_summary(db, scrip_code, ticker, False, None, None, True)
    return {
        "scrip_code": scrip_code,
        "is_bank": False,
        "roe_3y_avg": None,
        "roce_3y_avg": None,
        "financials_incomplete": True,
    }
