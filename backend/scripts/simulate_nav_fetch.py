from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav, search_mf_nav_by_name
import logging

# Set logging to capture what's happening
logging.basicConfig(level=logging.INFO)

def simulate_fetch(user_id):
    db = SessionLocal()
    mfs = db.query(MutualFund).filter(MutualFund.user_id == user_id).all()
    print(f"\n--- SIMULATING FETCH FOR USER {user_id} ---")
    print(f"{'ID':<5} | {'Scheme Name':<50} | {'AMFI':<10} | {'ISIN':<15} | {'Fetched NAV'}")
    print("-" * 100)
    
    for f in mfs:
        nav = None
        source = "None"
        
        # Following same logic as in mutual_fund.py
        if f.amfi_code or f.isin:
            nav = fetch_mf_nav(amfi_code=f.amfi_code, isin=f.isin)
            if nav: source = "AMFI/ISIN"
            
        if nav is None:
            search_result = search_mf_nav_by_name(f.scheme_name)
            if search_result and isinstance(search_result, dict):
                nav = search_result.get('nav')
                source = "Name Search"
            else:
                nav = search_result
                source = "Name Search (Legacy)"
        
        print(f"{f.id:<5} | {f.scheme_name[:50]:<50} | {f.amfi_code or 'None':<10} | {f.isin or 'None':<15} | {nav} ({source})")
    
    db.close()

# Simulate for both
simulate_fetch(1) # testuser1
simulate_fetch(2) # holder M user
