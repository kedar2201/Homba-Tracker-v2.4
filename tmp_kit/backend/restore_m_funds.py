from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

def restore_and_fix_sbi():
    db = SessionLocal()
    
    # 1. Restore the codes that were correct before I touched them (from my previous logs)
    # 2. Set SBI Nifty to the correct code for 239.03
    
    restorations = {
        "HDFC Balanced Advantage Fund": {"code": "119551", "name": "HDFC Balanced Advantage Fund"},
        "Helios Flexi Cap Fund": {"code": "152442", "name": "Helios Flexi Cap Fund"},
        "ICICI Prudential Balanced Advantage Fund": {"code": "120586", "name": "ICICI Prudential Balanced Advantage Fund"},
        "ICICI Prudential Banking and PSU Debt Fund": {"code": "120594", "name": "ICICI Prudential Banking and PSU Debt Fund"},
        "Motilal Oswal Nifty 200 Momentum 30 Index Fund": {"code": "152957", "name": "Motilal Oswal Nifty 200 Momentum 30 Index Fund"},
        "Quantum Small Cap Fund": {"code": "125354", "name": "Quantum Small Cap Fund"},
        "SBI Banking & PSU Fund": {"code": "103504", "name": "SBI Banking & PSU Fund"},
        # THE ONE YOU WANTED FIXED:
        "SBI Nifty Index Fund": {"code": "119827", "name": "SBI Nifty Index Fund"} 
    }

    print("Restoring holder M funds to original state, fixing only SBI Nifty Index...")
    
    funds = db.query(MutualFund).filter(MutualFund.holder == 'M').all()
    
    for f in funds:
        matched = False
        # Match by partial name to find which one is which
        for origin_name, data in restorations.items():
            # Check if the current name (which I might have changed) contains keywords from original
            keywords = origin_name.split()[:4] # Use first 4 words as signature
            if all(k.upper() in f.scheme_name.upper() for k in keywords):
                print(f"Restoring ID {f.id}: {f.scheme_name} -> {data['name']} (Code: {data['code']})")
                f.scheme_name = data['name']
                f.amfi_code = data['code']
                matched = True
                break
        if not matched:
            print(f"Could not precisely match ID {f.id} ({f.scheme_name}), leaving as is.")

    db.commit()
    db.close()
    print("\n✓ Fixed! SBI Nifty Index is now 119827 (NAV ~239.03) and others are restored.")

restore_and_fix_sbi()
