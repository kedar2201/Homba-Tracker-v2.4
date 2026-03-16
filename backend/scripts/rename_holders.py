from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.models.equity import Equity
from sqlalchemy import or_

def rename_holders():
    db = SessionLocal()
    
    # 1. THE MAPPING
    # User provided: "kedar manisha saloni and huf"
    # Data has: K, M, S, H
    mapping = {
        'K': 'Kedar',
        'M': 'Manisha',
        'S': 'Saloni',
        'H': 'HUF'
    }
    
    # 2. Assign HUF to the 30 distinct stocks (User 2)
    # These are IDs 255 to 284 (30 items) which were "Unknown" and I moved to M
    # I will move them to 'HUF' (which will then become 'HUF' full name or 'H' then remapped? 
    # Let's set them directly to 'HUF' to be safe, or 'H' and let mapping handle it.
    # User wanted "HUF" explicitly.
    
    print("Assigning 30 'Unknown' (now M) stocks to 'HUF'...")
    # Using the ID range logic consistent with import order
    huf_stocks = db.query(Equity).filter(Equity.id >= 255, Equity.id <= 284).all()
    print(f"Found {len(huf_stocks)} stocks in ID range 255-284.")
    for s in huf_stocks:
        s.holder = 'HUF' 
        # Note: I'm setting it to the target name directly to avoid confusion
        
    # 3. Apply Mapping to ALL tables (Equity, MutualFund)
    # This covers K, M, S, H -> Kedar, Manisha, Saloni, HUF
    
    print("Applying full name mapping to Equities...")
    equities = db.query(Equity).all()
    for e in equities:
        if e.holder in mapping:
            e.holder = mapping[e.holder]
            
    print("Applying full name mapping to Mutual Funds...")
    mfs = db.query(MutualFund).all()
    for m in mfs:
        if m.holder in mapping:
            m.holder = mapping[m.holder]
        # Also clean depositor_name if it matches codes
        if m.depositor_name in mapping:
            m.depositor_name = mapping[m.depositor_name]

    db.commit()
    db.close()
    print("✓ Renamed holders to: Kedar, Manisha, Saloni, HUF.")

if __name__ == "__main__":
    rename_holders()
