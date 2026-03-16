
from app.database import SessionLocal
from app.models.equity import Equity

def check_valuation():
    db = SessionLocal()
    try:
        equities = db.query(Equity).all()
        print(f"Total Equities in DB (All Users): {len(equities)}")
        
        current_eq_val = 0
        active_count = 0
        sold_count = 0
        
        print("\n--- DETAILED EQUITY SUMMATION ---")
        for e in equities:
            # Replicate the logic from backfill_nav.py
            status_str = str(e.status) if e.status else "None"
            
            price = e.current_price or e.buy_price or 0
            val = price * e.quantity
            
            # Check SGB
            is_sgb = e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper())
            
            if is_sgb:
                print(f"[SKIP-SGB] {e.symbol} Status={status_str} Val={val}")
                continue
                
            if "SOLD" in status_str:
                sold_count += 1
                # print(f"[SKIP-SOLD] {e.symbol} Status={status_str} Val={val}")
            else:
                active_count += 1
                current_eq_val += val
                if val > 1000000: # Print large contributors
                    print(f"[ACTIVE] {e.symbol} Status={status_str} Qty={e.quantity} Price={price} Val={val}")
                    
        print("\n--- SUMMARY ---")
        print(f"Active equities counted: {active_count}")
        print(f"Sold equities skipped: {sold_count}")
        print(f"Calculated Active Equity Value: {current_eq_val}")
        
        if current_eq_val > 100000000:
            print("CRITICAL: Value is > 10 Cr. Filter likely failed or massive invalid active holding exists.")

    finally:
        db.close()

if __name__ == "__main__":
    check_valuation()
