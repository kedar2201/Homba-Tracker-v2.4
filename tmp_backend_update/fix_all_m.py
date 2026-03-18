import requests
from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

def get_latest_amfi():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    resp = requests.get(url)
    return resp.text.splitlines()

def fix_all_holder_m():
    lines = get_latest_amfi()
    db = SessionLocal()
    funds = db.query(MutualFund).filter(MutualFund.holder == 'M').all()
    
    print(f"{'Name':<40} | {'Current Code':<10} | {'Suggested Code':<10} | {'New NAV'}")
    print("-" * 80)
    
    for f in funds:
        # Search for Direct Growth version of this fund
        target_name = f.scheme_name.upper().replace("REGULAR", "").replace("-", " ").strip()
        if "DIRECT" not in target_name:
            target_name += " DIRECT"
        if "GROWTH" not in target_name:
            target_name += " GROWTH"
            
        best_code = None
        best_nav = None
        best_match_name = ""
        
        # Simplified matching
        words = [w for w in target_name.split() if len(w) > 3]
        for line in lines:
            if ";" in line:
                parts = line.split(';')
                if len(parts) >= 5:
                    name = parts[3].upper()
                    if all(word in name for word in words) and "DIRECT" in name and "GROWTH" in name:
                        best_code = parts[0]
                        best_nav = parts[4]
                        best_match_name = parts[3]
                        break
        
        if best_code:
            print(f"{f.scheme_name[:40]:<40} | {f.amfi_code:<10} | {best_code:<10} | {best_nav}")
            f.amfi_code = best_code
            # Also update name if needed to reflect Direct Growth
            if "DIRECT" not in f.scheme_name.upper():
                f.scheme_name = best_match_name
        else:
            print(f"{f.scheme_name[:40]:<40} | {f.amfi_code:<10} | Not found")
            
    db.commit()
    db.close()

fix_all_holder_m()
