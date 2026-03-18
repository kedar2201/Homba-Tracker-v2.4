from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.fixed_deposit import FixedDeposit
from ..models.equity import Equity
from ..models.mutual_fund import MutualFund
from ..models.other_asset import OtherAsset
from ..auth.auth import get_current_user
from ..models.user import User
from datetime import date

router = APIRouter(tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Ultra-fast dashboard summary using only stored data"""
    
    # FD Total (Active only)
    today = date.today()
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == current_user.id).all()
    fd_total = sum(f.principal for f in fds if f.maturity_date and f.maturity_date >= today)
    
    # Equity Total (using stored prices)
    equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    equity_total = 0
    bonds_total = 0
    bonds_count = 0
    equity_invested = 0
    total_qty = 0
    
    for e in equities:
        price = e.current_price or e.buy_price or 0
        value = price * e.quantity
        
        if e.symbol.startswith("SGB"):
            bonds_total += value
            bonds_count += 1
        else:
            equity_total += value
            equity_invested += (e.buy_price * e.quantity)
            total_qty += e.quantity
    
    # Calculate NAV and P&L
    equity_nav = (equity_total / total_qty) if total_qty > 0 else 0
    equity_pnl_pct = ((equity_total - equity_invested) / equity_invested * 100) if equity_invested > 0 else 0
    
    # MF Total (using stored NAVs)
    mfs = db.query(MutualFund).filter(MutualFund.user_id == current_user.id).all()
    mf_total = 0
    for m in mfs:
        if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
            # SGB in MF table
            bonds_total += (7750.0 * m.units)  # Mock gold price
            bonds_count += 1
        else:
            # Use stored NAV or fallback
            nav = m.current_nav or 50.0
            mf_total += nav * m.units
    
    # Other Assets
    other_assets = db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()
    other_total = sum(a.valuation for a in other_assets)
    
    total = fd_total + equity_total + mf_total + other_total + bonds_total
    
    return {
        "fd": round(fd_total, 2),
        "equity": round(equity_total, 2),
        "mf": round(mf_total, 2),
        "bonds": round(bonds_total, 2),
        "other": round(other_total, 2),
        "total": round(total, 2),
        "equity_nav": round(equity_nav, 2),
        "equity_pnl_pct": round(equity_pnl_pct, 2),
        "count": {
            "fd": len(fds),
            "equity": len(equities) - bonds_count,
            "mf": len(mfs) - sum(1 for m in mfs if (m.interest_rate and m.interest_rate > 0) or "sgb" in m.scheme_name.lower()),
            "bonds": bonds_count,
            "other": len(other_assets)
        }
    }

@router.get("/growth")
def get_growth_analysis(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Return empty for now to prevent timeout"""
    return []
