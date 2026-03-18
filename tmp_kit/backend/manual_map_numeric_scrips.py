from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.models.equity import Equity
from sqlalchemy import text

def manual_update():
    db = SessionLocal()
    try:
        # Final verified mappings
        # Timex: BSE 500414.BO is reliable.
        # ZF: NSE ZFCVINDIA.NS is reliable.
        # Eureka Forbes: NSE EUREKAFORB.NS is reliable.
        mappings = {
            "NSE:500414": "500414.BO", 
            "BOM:500414": "500414.BO",
            "NSE:533023": "ZFCVINDIA.NS", 
            "BOM:533023": "533023.BO",
            "NSE:543482": "EUREKAFORB.NS", 
            "BOM:543482": "543482.BO"
        }
        
        for sym, yahoo_sym in mappings.items():
            print(f"Mapping {sym} -> {yahoo_sym}...")
            # Update PriceCache
            pc = db.query(PriceCache).filter(PriceCache.symbol == sym).first()
            if pc:
                pc.yahoo_symbol = yahoo_sym
                pc.yahoo_symbol_locked = True
                print(f"  PriceCache updated.")
            else:
                # Create if missing to ensure data fetching works for these requested scrips
                pc = PriceCache(symbol=sym, yahoo_symbol=yahoo_sym, yahoo_symbol_locked=True)
                db.add(pc)
                print(f"  PriceCache created.")
                
            # Update Equities
            db.execute(
                text("UPDATE equities SET yahoo_symbol = :ys, yahoo_symbol_locked = 1 WHERE symbol = :sym"),
                {"ys": yahoo_sym, "sym": sym}
            )
            print(f"  Equities table updated.")
            
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    manual_update()
