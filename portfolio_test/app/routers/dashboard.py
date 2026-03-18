from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.fixed_deposit import FixedDeposit
from ..models.equity import Equity
from ..models.mutual_fund import MutualFund
from ..models.other_asset import OtherAsset
from ..auth.auth import get_current_user
from ..models.user import User
from datetime import date, datetime, timedelta

from ..services.market_data import fetch_mf_nav, search_mf_nav_by_name
from ..services.calculations import MOCK_MF_NAVS

router = APIRouter(tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Ultra-fast dashboard summary using only stored data"""
    try:
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
        
        # Unit Tracking
        eq_buy_units = 0.0
        eq_sell_units = 0.0
        mf_buy_units = 0.0
        mf_sell_units = 0.0
        
        from ..models.equity import EquityStatus
        
        for e in equities:
            is_sgb = e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper())
            
            if is_sgb:
                pass
            else:
                eq_buy_units += (e.buy_units or 0.0)
                eq_sell_units += (e.sell_units or 0.0)
            
            is_active = (e.status == EquityStatus.ACTIVE or e.status is None)
            
            if is_active:
                price = e.current_price or e.buy_price or 0
                value = price * e.quantity
                
                if is_sgb:
                    bonds_total += value
                    bonds_count += 1
                else:
                    equity_total += value
                    equity_invested += (e.buy_price * e.quantity)
                    total_qty += e.quantity
        
        net_eq_units = eq_buy_units - eq_sell_units
        equity_portfolio_nav = (equity_total / net_eq_units) if net_eq_units > 0 else 100.0
        equity_pnl_pct = ((equity_total - equity_invested) / equity_invested * 100) if equity_invested > 0 else 0
        
        # Ensure 'equity_nav' in the response strictly uses the portfolio units
        equity_nav_display = equity_portfolio_nav
        
        mfs = db.query(MutualFund).filter(MutualFund.user_id == current_user.id).all()
        mf_total = 0
        mf_units_total = 0
        
        from ..models.mutual_fund import MFStatus
        
        for m in mfs:
            mf_buy_units += (m.p_buy_units or 0.0)
            mf_sell_units += (m.p_sell_units or 0.0)
            
            is_active = (m.status == MFStatus.ACTIVE or m.status is None)
            
            if is_active:
                if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
                    bonds_total += (7750.0 * m.units)
                    bonds_count += 1
                else:
                    mf_units_total += m.units
                    nav = None
                    if m.amfi_code or m.isin:
                        nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
                    
                    if nav is None:
                        res = search_mf_nav_by_name(m.scheme_name)
                        if res and isinstance(res, dict): nav = res.get('nav')
                        elif res: nav = res
                        
                    if nav is None:
                        nav = MOCK_MF_NAVS.get(m.isin, 0)
                        
                    if nav and nav > 0:
                        mf_total += (nav * m.units)
                    else:
                        mf_total += (m.invested_amount or 0)
        
        net_mf_units = mf_buy_units - mf_sell_units
        mf_portfolio_nav = (mf_total / net_mf_units) if net_mf_units > 0 else 100.0
        
        other_assets = db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()
        liquidable_categories = ["INSURANCE", "RETIREMENT", "GOLD", "BOND", "SAVINGS"]
        other_total = 0
        liquidable_total = 0
        liquidable_count = 0
        other_count = 0
        
        for a in other_assets:
            cat_str = a.category.value if hasattr(a.category, 'value') else str(a.category)
            if cat_str in liquidable_categories:
                liquidable_total += a.valuation
                liquidable_count += 1
            else:
                other_total += a.valuation
                other_count += 1
        
        # --- Star Rating Breakdown ---
        from ..models.rating import StockRatingSummary
        
        # 1. Group active equities by symbol
        active_equities = [e for e in equities if (e.status == EquityStatus.ACTIVE or e.status is None)]
        scrip_totals = {}
        for e in active_equities:
            code = e.symbol.upper().replace("NSE:", "").replace("BSE:", "").replace("BOM:", "")
            # Skip SGBs in rating breakdown
            if code.startswith("SGB"): continue
            
            price = e.current_price or e.buy_price or 0
            scrip_totals[code] = scrip_totals.get(code, 0) + (price * e.quantity)

        # 2. Fetch ratings
        scrip_codes = list(scrip_totals.keys())
        ratings = db.query(StockRatingSummary).filter(StockRatingSummary.scrip_code.in_(scrip_codes)).all()
        rating_map = {r.scrip_code: r.star_rating for r in ratings}
        
        # 3. Aggregate
        star_stats = {i: {"stars": i, "count": 0, "value": 0} for i in range(1, 6)}
        unrated_stats = {"stars": 0, "count": 0, "value": 0}

        for code, val in scrip_totals.items():
            stars = rating_map.get(code)
            if stars and stars in star_stats:
                star_stats[stars]["count"] += 1
                star_stats[stars]["value"] += val
            else:
                unrated_stats["count"] += 1
                unrated_stats["value"] += val
        
        star_breakdown = [star_stats[i] for i in range(5, 0, -1)]
        if unrated_stats["count"] > 0:
            star_breakdown.append(unrated_stats)

        total = fd_total + equity_total + mf_total + bonds_total + liquidable_total
        net_portfolio_units = net_eq_units + net_mf_units
        growth_portfolio_value = equity_total + mf_total
        
        portfolio_nav = (growth_portfolio_value / net_portfolio_units) if net_portfolio_units > 0 else 100.0
        
        return {
            "fd": round(fd_total, 2),
            "equity": round(equity_total, 2),
            "mf": round(mf_total, 2),
            "mf_nav_price": round(mf_portfolio_nav, 4),
            "mf_units": round(net_mf_units, 6),
            "bonds": round(bonds_total, 2),
            "other": round(other_total, 2),
            "liquidable_assets": round(liquidable_total, 2),
            "total": round(total, 2),
            "equity_nav": round(equity_nav_display, 4),
            "equity_portfolio_nav": round(equity_nav_display, 4),
            "equity_portfolio_units": round(net_eq_units, 6),
            "equity_pnl_pct": round(equity_pnl_pct, 2),
            "portfolio_nav": round(portfolio_nav, 4),
            "portfolio_units": round(net_portfolio_units, 6),
            "star_breakdown": star_breakdown,
            "count": {
                "fd": len(fds),
                "equity": len(equities) - bonds_count,
                "mf": len(mfs) - sum(1 for m in mfs if (m.interest_rate and m.interest_rate > 0) or "sgb" in m.scheme_name.lower()),
                "bonds": bonds_count,
                "liquidable": liquidable_count,
                "other": other_count
            }
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating dashboard summary: {str(e)}")
        # Return fallback structure to avoid frontend crash
        return {
            "fd": 0, "equity": 0, "mf": 0, "mf_nav_price": 100, "mf_units": 0,
            "bonds": 0, "other": 0, "liquidable_assets": 0, "total": 0,
            "equity_nav": 0, "equity_portfolio_nav": 100, "equity_portfolio_units": 0,
            "equity_pnl_pct": 0, "portfolio_nav": 100, "portfolio_units": 0,
            "count": {"fd": 0, "equity": 0, "mf": 0, "bonds": 0, "liquidable": 0, "other": 0}
        }


@router.get("/growth")
def get_growth_analysis(
    period: str = "1year",
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Growth chart — % change from first NAV in the chosen period vs Nifty/Sensex"""
    from datetime import date, datetime, timedelta
    import yfinance as yf
    
    # Period -> days mapping
    period_map = {
        "1week":  (7,    "1mo"),
        "qtr":    (90,   "3mo"),
        "half":   (180,  "6mo"),
        "1year":  (365,  "1y"),
        "2year":  (730,  "2y"),
        "3year":  (1095, "5y"),
        "5year":  (1825, "5y"),
    }
    days, yf_period = period_map.get(period, (365, "1y"))
    
    # Cache per user + period
    from ..services.market_data import get_cached_value, set_cached_value
    cache_key = f"growth_analysis_v21_{current_user.id}_{period}"
    cached_growth = get_cached_value(cache_key)
    if cached_growth:
        return cached_growth

    # Get NAV history from DB
    from app.models.nav_history import NAVHistory
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    history_records = db.query(NAVHistory).filter(
        NAVHistory.user_id == current_user.id,
        NAVHistory.timestamp >= cutoff_date,
        NAVHistory.nav_per_share > 0,
    ).order_by(NAVHistory.timestamp.asc()).all()
    
    portfolio_navs = {}
    for r in history_records:
        dt_str = r.timestamp.strftime("%Y-%m-%d")
        portfolio_navs[dt_str] = r.nav_per_share

    start_date_str = cutoff_date.strftime("%Y-%m-%d")

    # Fetch Nifty/Sensex directly via yfinance
    def fetch_index_history_filled(ticker: str, yf_per: str, filter_from: str, target_dates: list) -> dict:
        prices = {}
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=yf_per)
            raw_data = {dt.strftime("%Y-%m-%d"): row["Close"] for dt, row in hist.iterrows()}
            
            # Carry-forward logic for weekends/holidays
            last_val = None
            for d in sorted(target_dates):
                if d in raw_data:
                    last_val = raw_data[d]
                prices[d] = last_val
        except Exception as e: print(f"Error fetching {ticker}: {e}")
        return prices

    # Determine full date range from cutoff to today
    all_dates_range = []
    temp_date = cutoff_date
    today = datetime.utcnow()
    while temp_date <= today:
        all_dates_range.append(temp_date.strftime("%Y-%m-%d"))
        temp_date += timedelta(days=1)

    nifty_history = fetch_index_history_filled("^NSEI", yf_period, start_date_str, all_dates_range)
    sensex_history = fetch_index_history_filled("^BSESN", yf_period, start_date_str, all_dates_range)

    # Use intersection of record dates and benchmark availability
    all_dates = sorted(list(set(list(nifty_history.keys()) + list(sensex_history.keys()) + list(portfolio_navs.keys()))))
    if not all_dates: return []

    # Baselines (first available point in period)
    def find_baseline(hist_dict, dates_list):
        for d in dates_list:
            val = hist_dict.get(d)
            if val is not None and val > 0: return val
        return None

    base_nifty = find_baseline(nifty_history, all_dates)
    base_sensex = find_baseline(sensex_history, all_dates)
    base_nav = find_baseline(portfolio_navs, all_dates)

    combined_data = []
    for d_str in all_dates:
        p_val = None
        curr_p = portfolio_navs.get(d_str)
        if curr_p is not None and base_nav:
            p_val = round(((curr_p - base_nav) / base_nav) * 100, 2)
            
        n_val = None
        curr_n = nifty_history.get(d_str)
        if curr_n is not None and base_nifty:
            n_val = round(((curr_n - base_nifty) / base_nifty) * 100, 2)
            
        s_val = None
        curr_s = sensex_history.get(d_str)
        if curr_s is not None and base_sensex:
            s_val = round(((curr_s - base_sensex) / base_sensex) * 100, 2)

        combined_data.append({
            "date": d_str,
            "portfolio": p_val,
            "nifty": n_val,
            "sensex": s_val,
            "nav": portfolio_navs.get(d_str),
        })

    # Drop entries where all lines are empty
    combined_data = [cd for cd in combined_data if not (cd["portfolio"] is None and cd["nifty"] is None and cd["sensex"] is None)]
    
    set_cached_value(cache_key, combined_data)
    return combined_data


@router.get("/market-status")
def get_market_status():
    from ..services.market_data import fetch_live_stock_prices
    symbols = ["^NSEI", "^BSESN"]
    prices = fetch_live_stock_prices(symbols)
    
    results = []
    for sym, name in [("^NSEI", "NIFTY 50"), ("^BSESN", "SENSEX")]:
        info = prices.get(sym, {"price": 0, "prev_close": 0})
        price = info['price']
        prev_close = info.get('prev_close', price)
        change = price - prev_close
        percent = (change / prev_close * 100) if prev_close > 0 else 0
        
        results.append({
            "name": name,
            "symbol": sym,
            "price": round(price, 2),
            "change": round(change, 2),
            "percent": round(percent, 2)
        })
    return results
