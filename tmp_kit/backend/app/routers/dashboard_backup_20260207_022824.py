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

import logging
logger = logging.getLogger(__name__)

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
    
    # Calculate FD - Use PRINCIPAL for dashboard total (Exclude Matured FDs)
    fd_total = 0
    from datetime import date
    today = date.today()
    for f in fds:
        if f.maturity_date and f.maturity_date >= today:
            fd_total += f.principal
    
    # Calculate Equity
    prefixed_symbols = []
    from ..models.equity import Exchange
    for e in equities:
        if ":" in e.symbol:
            # Respect already prefixed symbols (like MUTF:FXAIX)
            prefixed_symbols.append(e.symbol)
        else:
            exc_str = e.exchange.value if hasattr(e.exchange, 'value') else str(e.exchange)
            prefix = "BOM" if exc_str == "BSE" else "NSE"
            prefixed_symbols.append(f"{prefix}:{e.symbol}")

    unique_symbols = list(set(prefixed_symbols))
    from ..services.market_data import fetch_live_stock_prices
    
    # PERFORMANCE GUARD: Dashboard summary MUST be instant.
    # Always use stored/cached prices. Use sync-prices (background) for updates.
    live_prices = {} 
    
    equity_total = 0
    bonds_total = 0
    bonds_count = 0
    updates_made = False
    
    for e in equities:
        if ":" in e.symbol:
            lookup_key = e.symbol
        else:
            exc_str = e.exchange.value if hasattr(e.exchange, 'value') else str(e.exchange)
            prefix = "BOM" if exc_str == "BSE" else "NSE"
            lookup_key = f"{prefix}:{e.symbol}"
        price_info = live_prices.get(lookup_key)
        
        if price_info and isinstance(price_info, dict):
            price = price_info.get('price') or e.current_price or e.buy_price or 0.0
            if price_info.get('price', 0) > 0:
                e.current_price = price_info['price']
                db.add(e)
                updates_made = True
        else:
            price = e.current_price or e.buy_price or 0.0
            
        value = price * e.quantity
        if e.symbol.startswith("SGB"):
            bonds_total += value
            bonds_count += 1
        else:
            equity_total += value
    
    if updates_made:
        db.commit()
    
    # Calculate MF
    mf_total = 0
    from ..services.market_data import fetch_mf_nav, search_mf_nav_by_name
    from ..services.calculations import get_sgb_current_value, MOCK_GOLD_PRICE, MOCK_MF_NAVS
    
    # SPEED OPTIMIZATION: Do not do remote fallback for MFs in dashboard
    for m in mfs:
        # SGB Case: These are valued by gold price, not NAV
        if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
            value = get_sgb_current_value(m.units)
            bonds_total += value
            bonds_count += 1
        else:
            nav = None
            if m.amfi_code or m.isin:
                nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin, skip_remote=True)
                
            if nav is None:
                # FAST PATH: Skip the slow fuzzy search refresh
                search_result = search_mf_nav_by_name(m.scheme_name, allow_refresh=False)
                if search_result:
                    if isinstance(search_result, dict):
                        nav = search_result.get('nav')
                    else:
                        nav = search_result
                
            if nav is None:
                nav = MOCK_MF_NAVS.get(m.isin, 50.0)
            
            mf_total += nav * m.units
    
    # Calculate Other Assets
    from ..models.other_asset import OtherAsset
    other_assets = db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()
    other_total = sum(a.valuation for a in other_assets)
    
    # Calculate NAV for Equity
    total_qty = sum(e.quantity for e in equities if not e.symbol.startswith("SGB"))
    equity_nav = (equity_total / total_qty) if total_qty > 0 else 0
    
    # Calculate Equity P&L % for dashboard trend
    equity_invested = sum((e.quantity * e.buy_price) for e in equities if not e.symbol.startswith("SGB"))
    equity_pnl_pct = ((equity_total - equity_invested) / equity_invested * 100) if equity_invested > 0 else 0
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
            "equity": len(equities) - sum(1 for e in equities if e.symbol.startswith("SGB")),
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
    from ..services.price_providers.service import price_service
    from datetime import date, datetime, timedelta
    
    # 1. Simple Cache Check
    from ..services.market_data import get_cached_value, set_cached_value
    cache_key = f"growth_analysis_{current_user.id}"
    cached_growth = get_cached_value(cache_key)
    if cached_growth:
        return cached_growth

    start_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # 2. Identify All Tickers for Bulk Fetch
    all_equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    
    # Sort by current value (or invested) to get the most important ones
    # Limit to top 25 for historical analysis to prevent YFinance timeout/hang
    all_equities.sort(key=lambda x: (x.quantity * (x.current_price or x.buy_price or 0)), reverse=True)
    top_equities = [e for e in all_equities if not e.symbol.upper().startswith("SGB")][:25]
    
    symbols_to_fetch = ["^NSEI", "^BSESN"]
    symbol_to_equity_id = {}
    total_qty = sum(e.quantity for e in top_equities)
    
    for e in top_equities:
        if ":" in e.symbol:
            lookup = e.symbol
        else:
            exc_str = e.exchange.value if hasattr(e.exchange, 'value') else str(e.exchange)
            prefix = "BOM" if exc_str == "BSE" else "NSE"
            lookup = f"{prefix}:{e.symbol}"
        symbols_to_fetch.append(lookup)
        symbol_to_equity_id[lookup] = e.id

    # 3. Bulk Fetch
    histories = price_service.get_history_bulk(symbols_to_fetch, start_date)
    nifty_history = histories.get("^NSEI", {})
    sensex_history = histories.get("^BSESN", {})
    
    logger.info(f"Growth Analysis: Symbols={symbols_to_fetch}")
    logger.info(f"Growth Analysis: Nifty days={len(nifty_history)}")
    
    if not nifty_history:
        return []

    equity_histories = {}
    for lookup, hist in histories.items():
        if lookup in ["^NSEI", "^BSESN"]: continue
        eid = symbol_to_equity_id.get(lookup)
        if eid and hist:
            equity_histories[eid] = hist
    
    # 3. Aggregate daily values
    combined_data = []
    sorted_dates = sorted(nifty_history.keys())
    
    if not sorted_dates:
        return []

    # Baselines for normalization (100)
    nifty_base = nifty_history[sorted_dates[0]]
    
    # Find sensex baseline (first available)
    sensex_base = None
    sensex_sorted_dates = sorted(sensex_history.keys())
    if sensex_sorted_dates:
        # Try to find exactly on the same start date first
        sensex_base = sensex_history.get(sorted_dates[0])
        if sensex_base is None:
            sensex_base = sensex_history[sensex_sorted_dates[0]]
    
    portfolio_base_value = 0
    for e in top_equities:
        # We need a base price for every equity to calculate growth accurately
        base_price = None
        if e.id in equity_histories:
            base_price = equity_histories[e.id].get(sorted_dates[0])
            
        if base_price is None:
            # Consistently use the same fallback as the daily loop
            base_price = (e.current_price or e.buy_price or 0)
            
        portfolio_base_value += base_price * e.quantity
    
    if portfolio_base_value == 0:
        portfolio_base_value = 1 # avoid div zero
    
    for dt in sorted_dates:
        nifty_raw = nifty_history[dt]
        nifty_growth = ((nifty_raw / nifty_base) - 1) * 100
        
        sensex_raw = sensex_history.get(dt)
        sensex_growth = None
        if sensex_raw is not None and sensex_base:
            sensex_growth = ((sensex_raw / sensex_base) - 1) * 100
        
        daily_portfolio_value = 0
        for e in top_equities:
            if e.id in equity_histories:
                val = equity_histories[e.id].get(dt)
                if val is not None:
                    daily_portfolio_value += val * e.quantity
                else:
                    daily_portfolio_value += (e.current_price or e.buy_price or 0) * e.quantity
            else:
                daily_portfolio_value += (e.current_price or e.buy_price or 0) * e.quantity
        
        portfolio_growth = ((daily_portfolio_value / portfolio_base_value) - 1) * 100
        daily_nav = (daily_portfolio_value / total_qty) if total_qty > 0 else 0
        
        combined_data.append({
            "date": dt,
            "nifty": round(nifty_growth, 2),
            "sensex": round(sensex_growth, 2) if sensex_growth is not None else None,
            "portfolio": round(portfolio_growth, 2),
            "nifty_actual": round(nifty_raw, 2),
            "sensex_actual": round(sensex_raw, 2) if sensex_raw is not None else None,
            "portfolio_actual": round(daily_portfolio_value, 2),
            "portfolio_nav": round(daily_nav, 2)
        })
        
    # Cache the result for 1 hour
    set_cached_value(cache_key, combined_data)
    return combined_data
