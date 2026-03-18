import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import User, Equity, FixedDeposit, MutualFund, OtherAsset, NAVHistory
from ..database import SessionLocal
from .calculations import calculate_fd_current_value, MOCK_GOLD_PRICE
from .market_data import fetch_mf_nav, search_mf_nav_by_name

logger = logging.getLogger(__name__)

def calculate_user_nav(db: Session, user_id: int):
    """
    Calculates the current NAV metrics for a specific user.
    Formula: Total Market Value / Total Equity Shares
    """
    # 1. Total Equity Value & Shares (Active only)
    equities = db.query(Equity).filter(
        Equity.user_id == user_id, 
        Equity.status == "ACTIVE"
    ).all()
    
    equity_value = 0
    equity_invested = 0
    bonds_value_equity = 0
    total_shares = 0
    
    for e in equities:
        current_price = e.current_price or e.buy_price or 0
        val = current_price * e.quantity
        
        # Exclude SGBs from Equity NAV, add to Bonds
        if e.symbol.startswith("SGB"):
            bonds_value_equity += val
        else:
            total_shares += e.quantity
            equity_value += val
            equity_invested += e.buy_price * e.quantity

    # 2. Fixed Deposits (Principal + Interest)
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == user_id).all()
    fd_value = 0
    fd_invested = 0
    for fd in fds:
        # Use current value logic
        # Map frequency enum to string if needed
        freq_str = fd.compounding_frequency.value if hasattr(fd.compounding_frequency, 'value') else str(fd.compounding_frequency)
        val = calculate_fd_current_value(fd.principal, fd.interest_rate, fd.start_date, freq_str)
        fd_value += val
        fd_invested += fd.principal

    # 3. Mutual Funds (Current NAV)
    mfs = db.query(MutualFund).filter(MutualFund.user_id == user_id).all()
    mf_value = 0
    mf_invested = 0
    
    # Pre-fetch AMFI cache to speed up loop
    from .market_data import refresh_amfi_nav_cache
    try: refresh_amfi_nav_cache()
    except: pass

    for m in mfs:
        mf_invested += m.invested_amount
        
        # SGB Logic for MFs
        if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
            mf_value += (MOCK_GOLD_PRICE * m.units)
        else:
            # NAV Logic
            nav = None
            if m.amfi_code or m.isin:
                nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
            
            if nav is None:
                res = search_mf_nav_by_name(m.scheme_name, allow_refresh=False)
                if res and isinstance(res, dict): nav = res.get('nav')
                elif res: nav = res
            
            if nav and nav > 0:
                mf_value += (nav * m.units)
            else:
                mf_value += m.invested_amount

    # 4. Liquidable Other Assets (Gold, Bonds, Savings)
    others = db.query(OtherAsset).filter(OtherAsset.user_id == user_id).all()
    liquid_value = 0
    liquid_categories = ["INSURANCE", "RETIREMENT", "GOLD", "BOND", "SAVINGS"]
    
    for o in others:
        cat_str = o.category.value if hasattr(o.category, 'value') else str(o.category)
        if cat_str in liquid_categories:
            liquid_value += o.valuation

    # Total Liquid Net Worth calculation
    total_value = equity_value + fd_value + mf_value + liquid_value
    total_invested = equity_invested + fd_invested + mf_invested + liquid_value

    # Portfolio Unit Tracking
    # For Equity: Use buy_units (normalized)
    eq_buy_units = sum(e.buy_units or 0.0 for e in equities)
    eq_sell_units = sum(e.sell_units or 0.0 for e in equities)
    net_eq_units = eq_buy_units - eq_sell_units
    
    nav_per_share = (equity_value / net_eq_units) if net_eq_units > 0 else 100.0

    # For MF: Use p_buy_units (normalized)
    mf_buy_units = sum(m.p_buy_units or 0.0 for m in mfs)
    mf_sell_units = sum(m.p_sell_units or 0.0 for m in mfs)
    net_mf_units = mf_buy_units - mf_sell_units
    
    # Recalculate MF Value for restricted NAV (excluding bonds)
    mf_total_value_for_nav = 0
    for m in mfs:
        if not (m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower()):
            # Same NAV fetch logic as before but concise
            nav = None
            if m.amfi_code or m.isin: nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
            if nav is None: 
                res = search_mf_nav_by_name(m.scheme_name, allow_refresh=False)
                nav = res.get('nav') if isinstance(res, dict) else res
            
            if nav and nav > 0: mf_total_value_for_nav += (nav * m.units)
            else: mf_total_value_for_nav += m.invested_amount

    mf_nav = (mf_total_value_for_nav / net_mf_units) if net_mf_units > 0 else 100.0

    return {
        "total_value": round(total_value, 2),
        "total_invested": round(total_invested, 2),
        "nav_per_share": round(nav_per_share, 4), # 4-6 decimals for fidelity
        "total_shares": round(net_eq_units + net_mf_units, 6), # Track PF Units, not Qty
        "mf_nav": round(mf_nav, 4)
    }


def capture_all_users_nav():
    """
    Scheduled task to capture NAV snapshots for all users.
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        logger.info(f"Starting NAV snapshot for {len(users)} users...")
        
        for user in users:
            metrics = calculate_user_nav(db, user.id)
            
            # The metrics["nav_per_share"] is already Unit-based thanks to our fix in calculate_user_nav
            snapshot = NAVHistory(
                user_id=user.id,
                total_value=metrics["total_value"],
                total_invested=metrics["total_invested"],
                nav_per_share=metrics["nav_per_share"], # Now correctly Value/PFUnits
                total_shares=metrics["total_shares"], # Still keep qty for reference
                mf_nav=metrics.get("mf_nav", 0.0), # Now correctly MFValue/MFPFUnits
                timestamp=datetime.utcnow()
            )
            db.add(snapshot)
            logger.info(f"Captured Snapshot for {user.username}: NAV={metrics['nav_per_share']}")
            
        db.commit()
    except Exception as e:
        logger.error(f"Error in capture_all_users_nav: {e}")
        db.rollback()
    finally:
        db.close()
