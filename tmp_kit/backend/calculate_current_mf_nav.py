import sys
import os

# Add the current directory to sys.path to make app importable
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav, search_mf_nav_by_name
from app.services.calculations import MOCK_MF_NAVS
from app.models.user import User

def calculate_mf_nav():
    db = SessionLocal()
    try:
        # Filter for newuser1 specifically
        users = db.query(User).filter(User.username == "newuser1").all()
        
        if not users:
            print("User 'newuser1' not found!")
            return

        for user in users:
            print(f"\nUser: {user.username} (ID: {user.id})")
            
            mfs = db.query(MutualFund).filter(MutualFund.user_id == user.id).all()
            
            mf_total_value = 0.0
            mf_total_units = 0.0
            
            count = 0
            for m in mfs:
                # Filter out SGBs/Bonds
                if (m.interest_rate and m.interest_rate > 0) or "sgb" in m.scheme_name.lower():
                    continue
                
                # It is a Mutual Fund
                count += 1
                
                # Fetch NAV
                nav = None
                if m.amfi_code or m.isin:
                    nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
                
                if nav is None:
                    res = search_mf_nav_by_name(m.scheme_name)
                    if res and isinstance(res, dict): nav = res.get('nav')
                    elif res: nav = res
                
                if nav is None:
                    nav = MOCK_MF_NAVS.get(m.isin, 0)
                
                current_value = 0
                if nav and nav > 0:
                    current_value = nav * m.units
                else:
                    current_value = m.invested_amount or 0
                
                mf_total_value += current_value
                mf_total_units += m.units
                
                print(f"  - {m.scheme_name[:40]:<40} | Units: {m.units:>10.4f} | NAV: {nav:>8.2f} | Status: {m.status} | ID: {m.id}")

            print("-" * 80)
            print(f"  Total MF Value: {mf_total_value:,.2f}")
            print(f"  Total MF Units: {mf_total_units:,.4f}")
            
            if mf_total_units > 0:
                mf_nav = mf_total_value / mf_total_units
                print(f"  Calculated MF NAV: {mf_nav:.4f}")
            else:
                print("  Calculated MF NAV: 0.0000")
            print("=" * 80)

    finally:
        db.close()

if __name__ == "__main__":
    calculate_mf_nav()
