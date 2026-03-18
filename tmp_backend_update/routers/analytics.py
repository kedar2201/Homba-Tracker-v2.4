from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.analytics import analytics_service
from ..calculations.technical_signals import calculate_dma_signal
from pydantic import BaseModel
from typing import Optional, List
from ..auth.auth import get_current_user
from ..models.user import User
from datetime import datetime, timedelta
from ..models.nav_history import NAVHistory
from sqlalchemy import asc

router = APIRouter(
    tags=["Analytics"],
)

class EPSUpdate(BaseModel):
    symbol: str
    eps: float

class GrowthUpdate(BaseModel):
    symbol: str
    growth: float

class YahooSymbolUpdate(BaseModel):
    symbol: str
    yahoo_symbol: str
    locked: bool = False

class AnalyticsResponse(BaseModel):
    symbol: str
    price: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    eps: Optional[float]
    pe: Optional[float]
    eps_growth: Optional[float]
    forward_eps: Optional[float]
    earnings_growth: Optional[float]
    yahoo_symbol: Optional[str]
    yahoo_symbol_locked: Optional[bool]
    updated_at: Optional[str]

    class Config:
        from_attributes = True

@router.get("/nav-history")
def get_nav_history(
    period: str = "all", 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(NAVHistory).filter(NAVHistory.user_id == current_user.id)
    
    # Date Filtering
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "qtr":
        start_date = now - timedelta(days=90)
    elif period == "half_year":
        start_date = now - timedelta(days=180)
    elif period == "year":
        start_date = now - timedelta(days=365)
    elif period == "3year":
        start_date = now - timedelta(days=365*3)
    else:
        start_date = None
        
    if start_date:
        query = query.filter(NAVHistory.timestamp >= start_date)
        
    history = query.order_by(asc(NAVHistory.timestamp)).all()
    
    return [
        {
            "timestamp": h.timestamp,
            "total_value": h.total_value,
            "nav_per_share": h.nav_per_share, # Equity NAV
            "mf_nav": h.mf_nav # MF NAV
        }
        for h in history
    ]

@router.get("/{symbol}")
def get_analytics_data(symbol: str, db: Session = Depends(get_db)):
    try:
        entry = analytics_service.get_analytics(db, symbol)
        if not entry:
            raise HTTPException(status_code=404, detail="Analytics not found for symbol")
        
        signal = calculate_dma_signal(entry.price, entry.ma50, entry.ma200)
        
        return {
            "symbol": entry.symbol,
            "price": entry.price,
            "ma50": entry.ma50,
            "ma200": entry.ma200,
            "signal": signal,
            "eps": entry.eps,
            "pe": entry.pe,
            "eps_growth": entry.eps_growth if entry.eps_growth is not None else 10.0,
            "forward_eps": entry.forward_eps,
            "earnings_growth": entry.earnings_growth,
            "yahoo_symbol": entry.yahoo_symbol,
            "yahoo_symbol_locked": entry.yahoo_symbol_locked,
            "updated_at": str(entry.analytics_updated_at) if entry.analytics_updated_at else None
        }
    except Exception as e:
        import traceback
        logging.error(f"Error in get_analytics_data for {symbol}: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/eps")
def update_eps(data: EPSUpdate, db: Session = Depends(get_db)):
    updated_entry = analytics_service.update_eps(db, data.symbol, data.eps)
    return {
        "symbol": updated_entry.symbol,
        "eps": updated_entry.eps,
        "pe": updated_entry.pe
    }

@router.post("/growth")
def update_growth(data: GrowthUpdate, db: Session = Depends(get_db)):
    updated_entry = analytics_service.update_growth(db, data.symbol, data.growth)
    return {
        "symbol": updated_entry.symbol,
        "eps_growth": updated_entry.eps_growth
    }

@router.post("/yahoo-symbol")
def update_yahoo_symbol(data: YahooSymbolUpdate, db: Session = Depends(get_db)):
    # Direct update in routers since it's a new field and service might not have it yet
    from ..models.market_data import PriceCache
    from ..models.equity import Equity
    from sqlalchemy import text
    
    entry = db.query(PriceCache).filter(PriceCache.symbol == data.symbol).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Symbol not found in cache")
    
    entry.yahoo_symbol = data.yahoo_symbol
    entry.yahoo_symbol_locked = data.locked
    
    # Also update equities table for consistency
    db.execute(
        text("UPDATE equities SET yahoo_symbol = :ys, yahoo_symbol_locked = :l WHERE symbol = :sym"),
        {"ys": data.yahoo_symbol, "l": 1 if data.locked else 0, "sym": data.symbol}
    )
    
    db.commit()
    return {
        "symbol": entry.symbol,
        "yahoo_symbol": entry.yahoo_symbol,
        "yahoo_symbol_locked": entry.yahoo_symbol_locked
    }

@router.post("/refresh/{symbol}")
def refresh_analytics(symbol: str, db: Session = Depends(get_db)):
    updated_entry = analytics_service.update_analytics(db, symbol)
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Symbol not found in cache")
    
    signal = calculate_dma_signal(updated_entry.price, updated_entry.ma50, updated_entry.ma200)
    
    return {
        "symbol": updated_entry.symbol,
        "price": updated_entry.price,
        "ma50": updated_entry.ma50,
        "ma200": updated_entry.ma200,
        "signal": signal,
        "eps": updated_entry.eps,
        "pe": updated_entry.pe,
        "eps_growth": updated_entry.eps_growth if updated_entry.eps_growth is not None else 10.0,
        "forward_eps": updated_entry.forward_eps,
        "earnings_growth": updated_entry.earnings_growth,
        "yahoo_symbol": updated_entry.yahoo_symbol,
        "yahoo_symbol_locked": updated_entry.yahoo_symbol_locked,
        "updated_at": updated_entry.analytics_updated_at
    }


