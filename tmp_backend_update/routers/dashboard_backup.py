from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.fixed_deposit import FixedDeposit
from ..models.equity import Equity
from ..models.mutual_fund import MutualFund
from ..services.calculations import (
    calculate_fd_maturity, 
    get_equity_current_value, 
    get_mf_current_value
)
from ..auth.auth import get_current_user
from ..models.user import User

router = APIRouter(tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Fetch all assets for user
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == current_user.id).all()
    equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    mfs = db.query(MutualFund).filter(MutualFund.user_id == current_user.id).all()
    
    # Calculate FD - Use PRINCIPAL for dashboard total
    fd_total = 0
    for f in fds:
        fd_total += f.principal
    
    # Calculate Equity
    equity_symbols = list(set(e.symbol for e in equities))
    from ..services.market_data import fetch_live_stock_prices
    live_prices = fetch_live_stock_prices(equity_symbols)
    
    equity_total = 0
    for e in equities:
        # fetch_live_stock_prices now returns {symbol: {'price': float, 'prev_close': float}}
        price_info = live_prices.get(e.symbol)
        if price_info and isinstance(price_info, dict):
            price = price_info.get('price') or e.current_price or 1000.0
        else:
            price = e.current_price or 1000.0
        equity_total += price * e.quantity
    
    # Calculate MF
    mf_total = 0
    from ..services.market_data import fetch_mf_nav, search_mf_nav_by_name
    from ..services.calculations import get_sgb_current_value, MOCK_GOLD_PRICE, MOCK_MF_NAVS
    
    for m in mfs:
        # SGB Case: These are valued by gold price, not NAV
        if m.interest_rate and m.interest_rate > 0:
            mf_total += get_sgb_current_value(m.units)
        else:
            nav = None
            if m.amfi_code or m.isin:
                nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
                
            if nav is None:
                nav = search_mf_nav_by_name(m.scheme_name)
                
            if nav is None:
                nav = MOCK_MF_NAVS.get(m.isin, 50.0)
            
            mf_total += nav * m.units
    
    # Calculate Other Assets
    from ..models.other_asset import OtherAsset
    other_assets = db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()
    other_total = sum(a.valuation for a in other_assets)
    
    # Console Net Worth = FD + Equity + MF (excluding 'Other Assets' as per user request)
    total = fd_total + equity_total + mf_total
    
    return {
        "fd": round(fd_total, 2),
        "equity": round(equity_total, 2),
        "mf": round(mf_total, 2),
        "other": round(other_total, 2),
        "total": round(total, 2),
        "count": {
            "fd": len(fds),
            "equity": len(equities),
            "mf": len(mfs),
            "other": len(other_assets)
        }
    }
