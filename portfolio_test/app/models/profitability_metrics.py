"""
Database models for stock profitability metrics (ROE & ROCE).

Two tables:
  - stock_profitability_metrics  : Year-wise raw computed values (audit trail)
  - stock_profitability_summary  : 3-year averaged values (what the UI reads)
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from ..database import Base
import enum


class DataSource(str, enum.Enum):
    Yahoo = "Yahoo"


class StockProfitabilityMetric(Base):
    """One row per scrip per fiscal year."""
    __tablename__ = "stock_profitability_metrics"

    id           = Column(Integer, primary_key=True, index=True)
    scrip_code   = Column(String, index=True, nullable=False)   # e.g. "RELIANCE"
    ticker       = Column(String, nullable=True)                # e.g. "RELIANCE.NS"
    fiscal_year  = Column(Integer, nullable=False)              # e.g. 2024
    roe          = Column(Float, nullable=True)                 # decimal, e.g. 0.1501 = 15.01%
    roce         = Column(Float, nullable=True)
    is_bank      = Column(Boolean, default=False, nullable=False)
    data_source  = Column(Enum(DataSource), default=DataSource.Yahoo)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class StockProfitabilitySummary(Base):
    """One row per scrip – the 3-year average (UI reads this)."""
    __tablename__ = "stock_profitability_summary"

    id            = Column(Integer, primary_key=True, index=True)
    scrip_code    = Column(String, index=True, nullable=False, unique=True)
    ticker        = Column(String, nullable=True)
    is_bank       = Column(Boolean, default=False, nullable=False)
    roe_3y_avg    = Column(Float, nullable=True)   # already percent, e.g. 15.01
    roce_3y_avg   = Column(Float, nullable=True)
    valid_till_fy = Column(Integer, nullable=True) # last FY included (e.g. 2025)
    financials_incomplete = Column(Boolean, default=False)
    last_refresh  = Column(DateTime(timezone=True), onupdate=func.now(),
                           server_default=func.now())
