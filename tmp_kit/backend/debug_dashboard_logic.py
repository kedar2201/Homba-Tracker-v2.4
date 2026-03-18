
from app.database import SessionLocal
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund
from app.models.fixed_deposit import FixedDeposit
from app.models.other_asset import OtherAsset
from datetime import datetime, date

def debug_breakdown():
    db = SessionLocal()
    try:
        # FDs
        today = date.today()
        fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == 1).all()
        fd_total = sum(f.principal for f in fds if f.maturity_date and f.maturity_date >= today)
        
        # Equity & Bonds (SGB)
        equities = db.query(Equity).filter(Equity.user_id == 1).all()
        eq_total = 0
        eq_bond_total = 0
        eq_bond_count = 0
        
        for e in equities:
            # Active Check
            status_str = str(e.status) if e.status else "ACTIVE"
            if "SOLD" in status_str: continue

            price = e.current_price or e.buy_price or 0
            val = price * e.quantity
            
            if e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper()):
                eq_bond_total += val
                eq_bond_count += 1
            else:
                eq_total += val

        # MF & Bonds (SGB)
        mfs = db.query(MutualFund).filter(MutualFund.user_id == 1).all()
        mf_total = 0
        mf_bond_total = 0
        
        for m in mfs:
            if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
                mf_bond_total += (7750.0 * m.units)
            else:
                # Naive NAV (Invested / Units) just for backfill proxy check
                # This is likely the weak link
                nav = m.invested_amount / m.units if m.units else 0
                mf_total += m.invested_amount or 0 # Using invested as fallback proxy
        
        # Other Assets
        others = db.query(OtherAsset).filter(OtherAsset.user_id == 1).all()
        liquidable_categories = ["INSURANCE", "RETIREMENT", "GOLD", "BOND", "SAVINGS"]
        liquid_total = 0
        
        for o in others:
             cat_str = o.category.value if hasattr(o.category, 'value') else str(o.category)
             if cat_str in liquidable_categories:
                 liquid_total += o.valuation
                 
        print("--- BACKFILL LOGIC BREAKDOWN ---")
        print(f"FD: {fd_total}")
        print(f"Equity: {eq_total}")
        print(f"MF (Invested Proxy): {mf_total}")
        print(f"Bonds (SGB): {eq_bond_total + mf_bond_total}")
        print(f"Liquidable: {liquid_total}")
        print(f"TOTAL: {fd_total + eq_total + mf_total + eq_bond_total + mf_bond_total + liquid_total}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_breakdown()
