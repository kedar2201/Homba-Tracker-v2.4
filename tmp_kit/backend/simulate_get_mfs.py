from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav, search_mf_nav_by_name

def simulate_get_mfs():
    db = SessionLocal()
    mf = db.query(MutualFund).filter(MutualFund.id == 16).first()
    db.close()
    
    if not mf:
        print("MF ID 16 not found")
        return

    print(f"Record 16: Name='{mf.scheme_name}', AMFI='{mf.amfi_code}', ISIN='{mf.isin}'")
    
    nav = None
    if mf.amfi_code or mf.isin:
        print(f"Calling fetch_mf_nav(amfi_code={mf.amfi_code}, isin={mf.isin})")
        nav = fetch_mf_nav(amfi_code=mf.amfi_code, isin=mf.isin)
        print(f"fetch_mf_nav returned: {nav}")

    if nav is None:
        print(f"Calling search_mf_nav_by_name('{mf.scheme_name}')")
        search_result = search_mf_nav_by_name(mf.scheme_name)
        print(f"search_mf_nav_by_name returned: {search_result}")
        if search_result:
            if isinstance(search_result, dict):
                nav = search_result.get('nav')
            else:
                nav = search_result
        print(f"Nav after search: {nav}")

    print(f"Final NAV for ID 16: {nav}")

if __name__ == "__main__":
    simulate_get_mfs()
