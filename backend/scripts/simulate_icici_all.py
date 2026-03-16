from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav, search_mf_nav_by_name

def trace_pp():
    db = SessionLocal()
    funds = db.query(MutualFund).filter(MutualFund.scheme_name.like("%Parag Parikh%")).all()
    db.close()
    
    print(f"{'ID':<4} | {'Name':<40} | {'ISIN':<10} | {'Method':<10} | {'NAV'}")
    print("-" * 85)
    
    for mf in funds:
        nav = None
        method = "None"
        
        # 1. Try AMFI Code or ISIN
        if mf.amfi_code or mf.isin:
            nav = fetch_mf_nav(amfi_code=mf.amfi_code, isin=mf.isin)
            if nav:
                method = "Code/ISIN"

        # 2. Fallback to name search
        if nav is None:
            res = search_mf_nav_by_name(mf.scheme_name)
            if res:
                if isinstance(res, dict):
                    nav = res['nav']
                    method = f"Name({res['code']})"
                else:
                    nav = res
                    method = "Name"

        print(f"{mf.id:<4} | {mf.scheme_name[:40]:<40} | {str(mf.isin):<10} | {method:<10} | {nav}")

if __name__ == "__main__":
    trace_pp()
