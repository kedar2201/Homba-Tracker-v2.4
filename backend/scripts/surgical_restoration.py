from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

def surgical_restore():
    db = SessionLocal()
    
    # ID: {'name': '...', 'code': '...'}
    fixes = {
        # User 1 (testuser1) - Restore to original working codes
        1: {'name': 'MF-quantum mutal fund', 'code': '107693'},
        2: {'name': 'Mf-Parag Parikh Flexi Cap - Dir Plan', 'code': '122639'},
        3: {'name': 'Mf-Parag Parikh Flexi Cap - Dir Plan', 'code': '122639'},
        4: {'name': 'Mf-Parag Parikh Flexi Cap - Dir Plan', 'code': '122639'},
        9: {'name': 'ICICI PRUDENTIAL BANKING & PSU DEBT FUND - DIRECT PLAN', 'code': '120256'},
        10: {'name': 'SBI BANKING & PSU FUND - DIRECT PLAN', 'code': '125503'},
        16: {'name': 'SBI Nifty Index Fund', 'code': '119827'}, # Fix to 239.03 code
        19: {'name': 'Helios Flexi Cap Fund', 'code': '152136'},
        23: {'name': 'HDFC BALANCED ADVANTAGE FUND - DIRECT PLAN', 'code': '118968'},
        27: {'name': 'HDFC BALANCED ADVANTAGE FUND - DIRECT PLAN', 'code': '118968'},
        
        # User 2 (Holder M) - Sync with working Direct Plan codes
        31: {'name': 'HDFC BALANCED ADVANTAGE FUND - DIRECT PLAN', 'code': '118968'},
        32: {'name': 'ICICI PRUDENTIAL BANKING AND PSU DEBT FUND - DIRECT PLAN', 'code': '120256'},
        33: {'name': 'SBI BANKING & PSU FUND - DIRECT PLAN', 'code': '125503'},
        34: {'name': 'HDFC Balanced Advantage Fund', 'code': '118968'},
        35: {'name': 'Helios Flexi Cap Fund', 'code': '152136'},
        36: {'name': 'ICICI Prudential Balanced Advantage Fund', 'code': '120586'},
        37: {'name': 'ICICI Prudential Banking and PSU Debt Fund', 'code': '120256'},
        38: {'name': 'Motilal Oswal Nifty 200 Momentum 30 Index Fund', 'code': '152957'},
        39: {'name': 'Quantum Small Cap Fund', 'code': '107693'},
        40: {'name': 'SBI Banking & PSU Fund', 'code': '125503'},
        41: {'name': 'SBI Nifty Index Fund', 'code': '119827'}, # Fix to 239.03 code
    }
    
    print("Starting surgical database restoration...")
    for mid, data in fixes.items():
        f = db.get(MutualFund, mid)
        if f:
            print(f"Updating ID {mid}: {f.scheme_name} -> {data['name']} (Code: {data['code']})")
            f.scheme_name = data['name']
            f.amfi_code = data['code']
        else:
            print(f"ID {mid} not found in database.")
            
    db.commit()
    db.close()
    print("✓ DATABASE FULLY RESTORED AND STABILIZED.")

if __name__ == "__main__":
    surgical_restore()
