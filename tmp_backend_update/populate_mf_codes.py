import requests
from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
import time

def populate_amfi_codes():
    db = SessionLocal()
    mfs = db.query(MutualFund).filter(MutualFund.amfi_code == None).all()
    print(f"Searching AMFI codes for {len(mfs)} funds...")
    
    cache = {}
    
    for mf in mfs:
        name = mf.scheme_name
        # Clean name
        clean_name = name.replace("Mf-", "").replace("MF-", "").split("-")[0].strip()
        
        if clean_name in cache:
            mf.amfi_code = cache[clean_name]
            continue
            
        print(f"Searching for: {clean_name}")
        try:
            url = f"https://api.mfapi.in/mf/search?q={clean_name}"
            res = requests.get(url, timeout=10)
            results = res.json()
            
            if results and len(results) > 0:
                # Pick the first one as best match
                # Ideally, we should do better matching (e.g. Growth vs IDCW)
                best_match = results[0]
                # Try to find a closer match for "Direct Plan" and "Growth"
                for r in results:
                    lower_r = r['schemeName'].lower()
                    if "direct" in lower_r and "growth" in lower_r:
                        best_match = r
                        break
                
                print(f"  Best Match: {best_match['schemeName']} ({best_match['schemeCode']})")
                mf.amfi_code = str(best_match['schemeCode'])
                cache[clean_name] = mf.amfi_code
            else:
                print(f"  No results for {clean_name}")
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(0.1) # Be nice to the API
        
    db.commit()
    db.close()
    print("Populate complete.")

if __name__ == "__main__":
    populate_amfi_codes()
