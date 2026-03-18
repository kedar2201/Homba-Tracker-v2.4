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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])

# Canonical Mapping for Grouping by Investor Code
INVESTOR_MAP = {
    "K": "Kedar Hombalkar",
    "M": "Manisha Hombalkar",
    "S": "Saloni Hombalkar",
    "H": "Kedar Hombalkar HUF"
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
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == current_user.id).all()
    current_year = datetime.now().year
    
    # Structure: { year: { canonical_investor_name: {interest, principal} } }
    investor_year_map = {}
    
    for f in fds:
        # Use Code-based grouping
        investor = get_canonical_investor(f.depositor_code, f.depositor_name)
        annual_interest = f.principal * (f.interest_rate / 100)
        
        start_year = f.start_date.year if f.start_date else current_year
        end_year = f.maturity_date.year if f.maturity_date else (current_year + 5)
        
        for yr in range(max(current_year, start_year), end_year + 1):
            if yr > current_year + 10: break
            if yr not in investor_year_map:
                investor_year_map[yr] = {}
            if investor not in investor_year_map[yr]:
                investor_year_map[yr][investor] = {"interest": 0, "principal": 0}
            
            investor_year_map[yr][investor]["interest"] += annual_interest
            investor_year_map[yr][investor]["principal"] += f.principal

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
                "tax": round(tax, 2)
            })
            
        final_report.append({
            "year": year,
            "interest": round(year_interest, 2),
            "principal": round(year_principal, 2),
            "tax_expected": round(year_total_tax, 2),
            "investor_breakdown": sorted(investors_detail, key=lambda x: x["interest"], reverse=True)
        })
        
    return final_report

@router.get("/non-performing-equities")
def get_non_performing_equities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    
    merged = {}
    for e in equities:
        if not e.symbol: continue
        sym = e.symbol.strip().upper()
        # Filter out INDEX codes or other junk
        if sym.startswith("INDEX"): continue
        
        # Determine exchange prefix for lookups
        # Try to infer from symbol or use default NSE
        prefix = "NSE"
        clean_sym = sym
        if ":" in sym:
            prefix, clean_sym = sym.split(":", 1)
        
        lookup_key = f"{prefix}:{clean_sym}"
        if lookup_key not in merged:
            merged[lookup_key] = {"qty": 0, "total_cost": 0, "current_price": e.current_price or 0, "operators": set(), "symbol_only": clean_sym}
        
        merged[lookup_key]["qty"] += e.quantity
        merged[lookup_key]["total_cost"] += (e.buy_price * e.quantity)
        
        op_name = get_canonical_investor(e.holder)
        merged[lookup_key]["operators"].add(op_name)
            
    from ..services.market_data import fetch_live_stock_prices
    symbols = list(merged.keys())
    live_prices = fetch_live_stock_prices(symbols)
    
    bad_performers = []
    for key, data in merged.items():
        if data["qty"] <= 0: continue
        
        price_info = live_prices.get(key)
        ltp = (price_info.get('price') if (price_info and isinstance(price_info, dict)) else data["current_price"]) or 0
            
        avg_buy_price = data["total_cost"] / data["qty"]
        pnl_pct = ((ltp - avg_buy_price) / avg_buy_price) * 100
        
        # Return all for frontend filtering
        if True:
            bad_performers.append({
                "symbol": data["symbol_only"],
                "operators": ", ".join(sorted(data["operators"])),
                "avg_buy_price": round(avg_buy_price, 2),
                "ltp": round(ltp, 2),
                "invested_amount": round(data["total_cost"], 2),
                "current_value": round(ltp * data["qty"], 2),
                "pnl_percentage": round(pnl_pct, 2),
                "total_loss": round((ltp - avg_buy_price) * data["qty"], 2),
                "total_qty": data["qty"]
            })
                
    return sorted(bad_performers, key=lambda x: x["pnl_percentage"])

@router.get("/projections")
def get_projections(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Standard 10-year projection logic
    from .dashboard import get_dashboard_summary
    summary = get_dashboard_summary(current_user, db)
    
    projections = []
    curr_eq, curr_mf, curr_fd = summary["equity"], summary["mf"], summary["fd"]
    withdrawal = 5000000
    
    for year in range(1, 11):
        if (curr_eq + curr_mf + curr_fd) <= 0: break
        
        growth_eq = curr_eq * 0.12
        growth_mf = curr_mf * 0.08
        growth_fd = curr_fd * 0.07
        
        curr_eq += growth_eq
        curr_mf += growth_mf
        curr_fd += growth_fd
        
        rem = withdrawal
        # Priority: FD -> MF -> EQ
        take = min(curr_fd, rem); curr_fd -= take; rem -= take
        if rem > 0: take = min(curr_mf, rem); curr_mf -= take; rem -= take
        if rem > 0: take = min(curr_eq, rem); curr_eq -= take; rem -= take
            
        projections.append({
            "year": datetime.now().year + year,
            "equity": round(curr_eq, 2), "mf": round(curr_mf, 2), "fd": round(curr_fd, 2),
            "total": round(curr_eq + curr_mf + curr_fd, 2),
            "growth_earned": round(growth_eq + growth_mf + growth_fd, 2)
        })
        
        # Step up withdrawal by 8% for next year
        withdrawal = withdrawal * 1.08
    return projections
