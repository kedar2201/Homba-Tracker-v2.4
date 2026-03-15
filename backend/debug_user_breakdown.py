
from app.database import SessionLocal
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund
from app.models.fixed_deposit import FixedDeposit
from app.models.other_asset import OtherAsset
from concurrent.futures import ThreadPoolExecutor

def analyze_user(user_id):
    db = SessionLocal()
    try:
        # Equities
        equities = db.query(Equity).filter(Equity.user_id == user_id).all()
        eq_val = 0
        bond_val = 0
        for e in equities:
            if e.status and "SOLD" in str(e.status): continue
            price = e.current_price or e.buy_price or 0
            val = price * e.quantity
            if e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper()):
                bond_val += val
            else:
                eq_val += val
        
        # MF
        mfs = db.query(MutualFund).filter(MutualFund.user_id == user_id).all()
        mf_val = 0
        mf_bond_val = 0
        for m in mfs:
            if m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower():
                mf_bond_val += (7750.0 * m.units)
            else:
                mf_val += (m.invested_amount or 0) # Proxy
                
        print(f"USER {user_id}: Equity={eq_val/1e7:.2f}Cr | MF={mf_val/1e7:.2f}Cr | Bonds(EQ+MF)={(bond_val+mf_bond_val)/1e5:.2f}L")
        return user_id, eq_val, mf_val, bond_val + mf_bond_val
    finally:
        db.close()

def audit_users():
    # Check User 1 and 2
    analyze_user(1)
    analyze_user(2)

if __name__ == "__main__":
    audit_users()
