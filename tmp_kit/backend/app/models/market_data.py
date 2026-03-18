from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from ..database import Base

class PriceCache(Base):
    __tablename__ = "price_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    price = Column(Float)
    prev_close = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Yahoo Mapping
    yahoo_symbol = Column(String, nullable=True)
    yahoo_symbol_locked = Column(Boolean, default=False)
    
    # Analytics
    ma50 = Column(Float, nullable=True)
    ma200 = Column(Float, nullable=True)
    eps = Column(Float, nullable=True) # TTM EPS
    # Forward Data
    eps_growth = Column(Float, nullable=True)
    forward_eps = Column(Float, nullable=True)
    earnings_growth = Column(Float, nullable=True)
    
    # Valuation for Radar
    pe = Column(Float, nullable=True)
    pe_avg_5y = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    
    # Growth Metrics
    eps_yoy_growth = Column(Float, nullable=True)
    debt_yoy_growth = Column(Float, nullable=True)
    
    # Market Data
    nifty_sma_5d = Column(Float, nullable=True)
    
    # Technical Indicators for Radar Engine
    high_30d = Column(Float, nullable=True)
    high_3m = Column(Float, nullable=True)
    avg_vol_20d = Column(Float, nullable=True)
    current_vol = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)

    # Quality Metrics for Radar Model 2Q
    roe = Column(Float, nullable=True)
    roce = Column(Float, nullable=True)
    ebit_margin = Column(Float, nullable=True)
    net_profit_margin = Column(Float, nullable=True)
    
    # Sector Specific Basics
    nim = Column(Float, nullable=True) # Net Interest Margin
    gnpa = Column(Float, nullable=True) # Gross NPA %
    solvency_ratio = Column(Float, nullable=True)
    ev_growth = Column(Float, nullable=True)
    
    analytics_updated_at = Column(DateTime, nullable=True)
