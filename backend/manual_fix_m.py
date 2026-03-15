from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

def manual_fix():
    db = SessionLocal()
    
    # Funds to fix for holder M
    fixes = {
        "SBI Nifty Index Fund": {"code": "119827", "isin": "INF200K01TE8"},
        "HDFC Balanced Advantage Fund": {"code": "118968", "isin": "INF200K01V30"}, # Added common ISIN for Direct Growth
        "ICICI Prudential Banking and PSU Debt Fund": {"code": "120256", "isin": "INF109K01Y62"},
        "SBI Banking & PSU Fund": {"code": "125503", "isin": "INF200K01V55"},
        "Quantum Small Cap Fund": {"code": "152107", "isin": "INF333K01S35"}, # Wait, is this the one with S35?
    }
    
    # Note: Quantum Small Cap Direct Growth often has S35 in its ISIN (INF333K01S35)
    # The user mentioned S35 earlier! Maybe they were talking about Quantum Small Cap?
    # "Quantum Small Cap Fund" is in the screenshot for holder M.
    
    for name_part, data in fixes.items():
        funds = db.query(MutualFund).filter(
            MutualFund.holder == 'M',
            MutualFund.scheme_name.like(f"%{name_part}%")
        ).all()
        
        for f in funds:
            print(f"Updating {f.scheme_name} (ID: {f.id}) to Code: {data['code']}, ISIN: {data['isin']}")
            f.amfi_code = data['code']
            f.isin = data['isin']
            # Update name to include "Direct Plan - Growth" to be clear
            if "DIRECT" not in f.scheme_name.upper():
                f.scheme_name = f"{f.scheme_name} - Direct Plan - Growth"
    
    db.commit()
    db.close()

manual_fix()
