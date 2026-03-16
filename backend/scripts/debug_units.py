
from app.database import SessionLocal
from app.models.equity import Equity

def check_units():
    db = SessionLocal()
    try:
        equities = db.query(Equity).filter(Equity.user_id == 1).all()
        print(f"Total Equities: {len(equities)}")
        
        total_units = 0
        total_invested = 0
        
        for e in equities:
            units = e.buy_units or 0
            invested = (e.buy_price or 0) * (e.quantity or 0)
            
            total_units += units
            total_invested += invested
            
            # Print sample
            if units == 0 and invested > 10000:
                print(f"WARNING: {e.symbol} has Invested {invested} but Units {units}")

        print(f"Total Invested: {total_invested}")
        print(f"Total Buy Units: {total_units}")
        
        if total_units > 0:
            print(f"Implied Initial NAV: {total_invested / total_units}")
        else:
            print("Total Units is 0")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_units()
