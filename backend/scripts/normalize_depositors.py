from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

def normalize_depositors():
    db = SessionLocal()
    
    # 1. Fix Holder H (User 1)
    # The depositor_name was incorrectly set to the Scheme Name
    h_funds = db.query(MutualFund).filter(MutualFund.holder == 'H').all()
    print(f"Fixing {len(h_funds)} funds for Holder H...")
    for f in h_funds:
        f.depositor_name = 'H'
        
    # 2. Fix Holder M (User 1)
    # Some had None, some had "M"
    m_funds = db.query(MutualFund).filter(MutualFund.holder == 'M').all()
    print(f"Fixing {len(m_funds)} funds for Holder M...")
    for f in m_funds:
        f.depositor_name = 'M'
        
    # 3. Fix Holder K (User 1)
    # Normalize "KEDAR HOMBALKAR" and missing holder
    k_funds = db.query(MutualFund).filter(
        (MutualFund.holder == 'K') | 
        (MutualFund.depositor_name.in_(['K', 'KEDAR HOMBALKAR']))
    ).all()
    print(f"Fixing {len(k_funds)} funds for Holder K...")
    for f in k_funds:
        f.holder = 'K'
        f.depositor_name = 'K'

    db.commit()
    db.close()
    print("✓ All depositor names normalized to 'H', 'M', 'K'.")

if __name__ == "__main__":
    normalize_depositors()
