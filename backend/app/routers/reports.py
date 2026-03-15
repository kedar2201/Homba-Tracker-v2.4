from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from ..database import get_db
from ..models.fixed_deposit import FixedDeposit
from ..models.equity import Equity
from ..models.mutual_fund import MutualFund
from ..models.other_asset import OtherAsset
from ..auth.auth import get_current_user
from ..models.user import User
from datetime import datetime, date, timedelta
import logging
import pandas as pd
from ..calculations.technical_signals import calculate_dma_signal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reports"])

# Canonical Mapping for Grouping by Investor Code
INVESTOR_MAP = {
    # Original Codes
    "K": "Kedar Hombalkar",
    "M": "Manisha Hombalkar",
    "S": "Saloni Hombalkar",
    "H": "Kedar Hombalkar HUF",
    "HUF": "Kedar Hombalkar HUF",
    # Full Names (to support recent DB updates)
    "Kedar": "Kedar Hombalkar",
    "Manisha": "Manisha Hombalkar",
    "Saloni": "Saloni Hombalkar",
    "Kedar Hombalkar": "Kedar Hombalkar",
    "Manisha Hombalkar": "Manisha Hombalkar",
    "Saloni Hombalkar": "Saloni Hombalkar",
    "Kedar Hombalkar HUF": "Kedar Hombalkar HUF"
}

def get_canonical_investor(code: str, name: str = "") -> str:
    """Normalize investor name based on the 4 codes: K, M, S, H."""
    if not code:
        return name or "Unknown"
    
    # Clean and uppercase code for case-insensitive matching
    clean_code = str(code).strip().upper()
    if clean_code in INVESTOR_MAP:
        return INVESTOR_MAP[clean_code]
    
    # Fallback logic if code is not K/M/S/H directly
    if name:
        name_upper = str(name).upper()
        if "HUF" in name_upper: return INVESTOR_MAP["H"]
        if "SALONI" in name_upper: return INVESTOR_MAP["S"]
        if "MANISHA" in name_upper: return INVESTOR_MAP["M"]
        if "KEDAR" in name_upper: return INVESTOR_MAP["K"]
        
    return name or clean_code or "Unknown"

def get_canonical_investor_details(code: str, name: str = "", broker: str = "") -> str:
    """Normalize investor name and add broker info if present."""
    display_name = get_canonical_investor(code, name)
    
    # Get abbreviated code
    rev_map = {
        "Kedar Hombalkar": "K",
        "Manisha Hombalkar": "M",
        "Saloni Hombalkar": "S",
        "Kedar Hombalkar HUF": "H"
    }
    short_code = rev_map.get(display_name, display_name[:1].upper())
    
    if broker:
        return f"{short_code} ({broker})"
    return short_code

def calculate_new_regime_tax_detailed(income: float) -> float:
    """ 
    Official New Tax Regime Slabs (Budget 2025 / AY 2026-27):
    - Up to 4.0L: Nil
    - 4L to 8L: 5% (Rebate 87A makes it Nil if total is <= 12L)
    - 8L to 12L: 10%
    - 12L to 16L: 15%
    - 16L to 20L: 20%
    - 20L to 24L: 25%
    - Above 24L: 30%
    - Standard Rebate 87A: Nil tax if income <= 12L
    """
    if income <= 1200000: 
        return 0.0
    
    tax = 0.0
    if income > 400000:
        tax += min(income - 400000, 400000) * 0.05
    if income > 800000:
        tax += min(income - 800000, 400000) * 0.10
    if income > 1200000:
        tax += min(income - 1200000, 400000) * 0.15
    if income > 1600000:
        tax += min(income - 1600000, 400000) * 0.20
    if income > 2000000:
        tax += min(income - 2000000, 400000) * 0.25
    if income > 2400000:
        tax += (income - 2400000) * 0.30
        
    # Standard 4% Health & Education Cess
    return round(tax * 1.04, 2)

@router.get("/fd-interest")
def get_fd_interest_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == current_user.id).all()
        current_year = datetime.now().year
        
        from ..services.calculations import calculate_fd_interest_for_fy
        investor_year_map = {}
        
        for f in fds:
            investor = get_canonical_investor(f.depositor_code, f.depositor_name)
            freq = f.compounding_frequency.value if (f.compounding_frequency and hasattr(f.compounding_frequency, 'value')) else "Yearly"
            
            # Calculate interest for the next 10 fiscal years
            for yr in range(current_year, current_year + 11):
                fy_start = date(yr, 4, 1)
                fy_end = date(yr + 1, 3, 31)
                
                # Active principal in this FY? (Overlap check)
                if f.start_date <= fy_end and f.maturity_date >= fy_start:
                    interest = calculate_fd_interest_for_fy(
                        f.principal, f.interest_rate, f.start_date, f.maturity_date, freq, yr
                    )
                    
                    if interest > 0:
                        if yr not in investor_year_map:
                            investor_year_map[yr] = {}
                        if investor not in investor_year_map[yr]:
                            investor_year_map[yr][investor] = {"interest": 0, "principal": 0, "fds": []}
                        
                        investor_year_map[yr][investor]["interest"] += interest
                        # Only add principal if it's still active at the START of the FY or later
                        if f.maturity_date >= fy_start:
                            investor_year_map[yr][investor]["principal"] += f.principal

                        # Add individual FD details for the report
                        investor_year_map[yr][investor]["fds"].append({
                            "bank_name": f.bank_name,
                            "fd_code": f.fd_code,
                            "principal": f.principal,
                            "interest_rate": f.interest_rate,
                            "start_date": f.start_date.isoformat() if f.start_date else None,
                            "maturity_date": f.maturity_date.isoformat() if f.maturity_date else None,
                            "interest_earned": round(interest, 2)
                        })

        final_report = []
        for year in sorted(investor_year_map.keys()):
            year_total_tax = 0
            investors_detail = []
            year_interest = 0
            year_principal = 0
            
            for name, data in investor_year_map[year].items():
                tax = calculate_new_regime_tax_detailed(data["interest"])
                year_total_tax += tax
                year_interest += data["interest"]
                year_principal += data["principal"]
                investors_detail.append({
                    "name": name,
                    "interest": round(data["interest"], 2),
                    "principal": round(data["principal"], 2),
                    "tax": round(tax, 2),
                    "fds": sorted(data["fds"], key=lambda x: x["interest_earned"], reverse=True)
                })
                
            final_report.append({
                "year": year,
                "interest": round(year_interest, 2),
                "principal": round(year_principal, 2),
                "tax_expected": round(year_total_tax, 2),
                "investor_breakdown": sorted(investors_detail, key=lambda x: x["interest"], reverse=True)
            })
            
        return final_report
    except Exception as e:
        logger.error(f"Error generating FD interest report: {str(e)}")
        return []


@router.get("/non-performing-equities")
def get_non_performing_equities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        from ..models.equity import EquityStatus
        from sqlalchemy import or_
        # Restore strict user_id filtering as per user instructions
        equities = db.query(Equity).filter(
            Equity.user_id == current_user.id,
            or_(Equity.status == EquityStatus.ACTIVE, Equity.status == None)
        ).all()

        
        debug_total_raw = sum(e.buy_price * e.quantity for e in equities if e.buy_price and e.quantity)
        print(f"DEBUG: user={current_user.username} (id={current_user.id}) - found {len(equities)} active equities. Raw Sum: {debug_total_raw}")
        
        merged = {}
        for e in equities:
            if not e.symbol: continue
            sym = e.symbol.strip().upper()
            scrip_name = (e.scrip_name or "").upper()
            
            # Filter out INDEX codes or SGBs (as per user request: "Equity Only")
            if sym.startswith("INDEX") or sym.startswith("SGB") or "SGB" in scrip_name: 
                continue


            
            # Determine exchange prefix for lookups from DB record
            from ..models.equity import Exchange
            exc_str = e.exchange.value if hasattr(e.exchange, 'value') else str(e.exchange)
            prefix = "BOM" if exc_str == "BSE" else "NSE"
            clean_sym = sym
            if ":" in sym:
                 _, clean_sym = sym.split(":", 1)
            
            lookup_key = f"{prefix}:{clean_sym}"
            if lookup_key not in merged:
                merged[lookup_key] = {
                    "qty": 0, 
                    "total_cost": 0, 
                    "current_price": e.current_price or 0, 
                    "breakdown": [], 
                    "symbol_only": clean_sym,
                    "instrument_type": e.instrument_type or "Stock",
                    "buy_units": 0
                }
            
            merged[lookup_key]["qty"] += e.quantity
            merged[lookup_key]["total_cost"] += (e.buy_price * e.quantity)
            merged[lookup_key]["buy_units"] += (e.buy_units or 0)
            
            op_detail = get_canonical_investor_details(e.holder, broker=e.broker)
            merged[lookup_key]["breakdown"].append({
                "holder": e.holder,
                "broker": e.broker,
                "label": op_detail,
                "qty": e.quantity,
                "avg_price": e.buy_price,
                "invested": e.buy_price * e.quantity
            })
        
        debug_merged_total = sum(d["total_cost"] for d in merged.values())
        print(f"DEBUG: Merged {len(merged)} scrips. Merged Total Invested: {debug_merged_total}")
                
        from ..services.market_data import fetch_live_stock_prices
        symbols = list(merged.keys())
        live_prices = fetch_live_stock_prices(symbols)
        
        bad_performers = []
        for key, data in merged.items():
            # Get fresh LTP if available, otherwise fallback to DB price (which might be older)
            price_info = live_prices.get(key)
            live_price = price_info.get('price') if (price_info and isinstance(price_info, dict)) else None
            
            # Use live price ONLY if it's positive. If it's 0 or None, use the DB price to prevent total value drops.
            ltp = (live_price if (live_price and live_price > 0) else data["current_price"]) or 0

            prev_close = (price_info.get('prev_close') if (price_info and isinstance(price_info, dict)) else None)
            
            # Daily Change Calculation
            daily_change = round(ltp - prev_close, 2) if prev_close else 0
            daily_pnl_percentage = round((daily_change / prev_close) * 100, 2) if (prev_close and prev_close > 0) else 0
            daily_pnl = round(daily_change * data["qty"], 2)

            avg_buy_price = data["total_cost"] / data["qty"]
            pnl_pct = ((ltp - avg_buy_price) / avg_buy_price) * 100
            
            # Return all for frontend filtering
            bad_performers.append({
                "symbol": data["symbol_only"],
                "operators": ", ".join(sorted(list(set(b["label"] for b in data["breakdown"])))),
                "breakdown": data["breakdown"],
                "instrument_type": data["instrument_type"],
                "avg_buy_price": round(avg_buy_price, 2),
                "ltp": round(ltp, 2),
                "invested_amount": round(data["total_cost"], 2),
                "current_value": round(ltp * data["qty"], 2),
                "pnl_percentage": round(pnl_pct, 2),
                "total_loss": round((ltp - avg_buy_price) * data["qty"], 2),
                "total_qty": data["qty"],
                "pf_units": round(data["buy_units"], 2),
                "daily_change": daily_change,
                "daily_pnl_percentage": daily_pnl_percentage,
                "daily_pnl": daily_pnl
            })
                    
        return sorted(bad_performers, key=lambda x: x["pnl_percentage"])
    except Exception as e:
        logger.error(f"Error generating non-performing equities report: {str(e)}")
        return []

    return projections

@router.get("/dma-signals")
def get_dma_signals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Calculate 50 DMA and 200 DMA for all active equities and return signals + summary.
    Bullish: CMP > 50 > 200 (or variations)
    Implemented with a 24h file cache to prevent timeout issues on large portfolios.
    """
    import os, json, time
    from ..services.price_providers.service import price_service
    import pandas as pd
    
    # Simple File Cache Implementation
    CACHE_FILE = ".dma_signals_cache.json"
    CACHE_EXPIRY = 24 * 60 * 60 # 24 hours
    
    user_id_str = str(current_user.id)
    
    # Try reading cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                full_cache = json.load(f)
                if user_id_str in full_cache:
                    cached_data = full_cache[user_id_str]
                    if (time.time() - cached_data.get("timestamp", 0)) < CACHE_EXPIRY:
                        logger.info(f"Returning CACHED DMA signals for user {user_id_str}")
                        return cached_data.get("data", {})
    except Exception as ce:
        logger.warning(f"DMA Cache read failed: {ce}")

    try:
        # 1. Get all active equities for this user
        from ..models.equity import EquityStatus
        equities = db.query(Equity).filter(
            Equity.user_id == current_user.id,
            Equity.status == EquityStatus.ACTIVE
        ).all()
        if not equities:
            return {"results": [], "summary": {}}
            
        # Group by symbol to get total quantity
        sym_to_qty = {}
        for e in equities:
            if not e.symbol or e.symbol.startswith("INDEX"): continue
            sym = e.symbol.strip().upper()
            sym_to_qty[sym] = sym_to_qty.get(sym, 0) + (e.quantity or 0)
            
        symbols = list(sym_to_qty.keys())
        
        # 2. Fetch 1 year history
        start_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        
        logger.info(f"Generating FRESH DMA signals for {len(symbols)} symbols")
        history_data = price_service.get_history_bulk(symbols, start_date)
        
        results = []
        summary = {
            "bullish": {"count": 0, "value": 0, "percentage": 0},
            "bearish": {"count": 0, "value": 0, "percentage": 0},
            "long term bullish, near term bearish": {"count": 0, "value": 0, "percentage": 0},
            "near term bullish, long term bearish": {"count": 0, "value": 0, "percentage": 0},
            "neutral": {"count": 0, "value": 0, "percentage": 0}
        }
        total_portfolio_value = 0
        
        for symbol in symbols:
            data = history_data.get(symbol, {})
            # Need at least 200 days for 200 DMA
            if not data or len(data) < 200:
                continue
                
            qty = sym_to_qty[symbol]
            if qty <= 0: continue
            
            # Convert to DataFrame
            df = pd.DataFrame(list(data.items()), columns=['date', 'price'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df.set_index('date', inplace=True)
            
            # Calculate DMAs
            df['50_dma'] = df['price'].rolling(window=50).mean()
            df['200_dma'] = df['price'].rolling(window=200).mean()
            
            last_row = df.iloc[-1]
            cmp = last_row['price']
            dma_50 = last_row['50_dma']
            dma_200 = last_row['200_dma']
            
            if pd.isna(dma_50): dma_50 = 0
            if pd.isna(dma_200): dma_200 = 0
            
            signal = calculate_dma_signal(cmp, dma_50, dma_200)
            
            value = cmp * qty
            total_portfolio_value += value
            
            summary[signal]["count"] += 1
            summary[signal]["value"] += value
                
            results.append({
                "symbol": symbol,
                "cmp": round(cmp, 2),
                "qty": qty,
                "value": round(value, 2),
                "dma_50": round(dma_50, 2),
                "dma_200": round(dma_200, 2),
                "signal": signal,
                "dma_50_status": "Above" if cmp >= dma_50 else "Below",
                "dma_200_status": "Above" if cmp >= dma_200 else "Below"
            })
            
        # Calculate percentages
        for trend in summary:
            if total_portfolio_value > 0:
                summary[trend]["percentage"] = round((summary[trend]["value"] / total_portfolio_value) * 100, 2)
            summary[trend]["value"] = round(summary[trend]["value"], 2)
            
        final_data = {
            "results": sorted(results, key=lambda x: x["value"], reverse=True),
            "summary": summary,
            "total_value": round(total_portfolio_value, 2)
        }

        # Write to Cache
        try:
            full_cache = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    full_cache = json.load(f)
            
            full_cache[user_id_str] = {
                "timestamp": time.time(),
                "data": final_data
            }
            
            with open(CACHE_FILE, "w") as f:
                json.dump(full_cache, f)
            logger.info(f"DMA signals CACHED successfully for user {user_id_str}")
        except Exception as we:
            logger.error(f"DMA Cache write failed: {we}")
            
        return final_data
    except Exception as e:
        logger.error(f"Error generating DMA signals: {str(e)}")
        return {"results": [], "summary": {}}
