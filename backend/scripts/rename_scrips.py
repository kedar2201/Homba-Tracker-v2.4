import os
from sqlalchemy import text
from app.database import SessionLocal
from app.models.equity import Equity
from app.models.market_data import PriceCache
from app.services.analytics import analytics_service
from app.services.rating_engine import compute_and_store_rating
from app.services.profitability_service import compute_and_store_profitability

# Mapping from Numeric Code to String Name and Yahoo Ticker
RENAME_MAP = {
    "500414": {"name": "TIMEX", "yahoo": "TIMEXWATCH.NS"},
    "533023": {"name": "ZFCVINDIA", "yahoo": "ZFCVINDIA.NS"},
    "543482": {"name": "EUREKAFORB", "yahoo": "EUREKAFORB.NS"},
    "543396": {"name": "PAYTM", "yahoo": "PAYTM.NS"},
    "500049": {"name": "BEL", "yahoo": "BEL.NS"},
    "532540": {"name": "TCS", "yahoo": "TCS.NS"},
    "532822": {"name": "IDEA", "yahoo": "IDEA.NS"},
    "514162": {"name": "CAMLINFINE", "yahoo": "CAMLINFINE.NS"},
    "532475": {"name": "HINDWAREAP", "yahoo": "HINDWAREAP.NS"},
    "500696": {"name": "HINDUNILVR", "yahoo": "HINDUNILVR.NS"},
    "533121": {"name": "EXPLEOSOL", "yahoo": "EXPLEOSOL.NS"},
    "523716": {"name": "ASHIANA", "yahoo": "ASHIANA.NS"},
    "539448": {"name": "INDIGO", "yahoo": "INDIGO.NS"},
    "500112": {"name": "SBIN", "yahoo": "SBIN.NS"},
    "500182": {"name": "HEROMOTOCO", "yahoo": "HEROMOTOCO.NS"},
}

def run_rename():
    db = SessionLocal()
    print("Starting scrip rename process...")
    
    # 1. Update Equity table
    equities = db.query(Equity).all()
    updated_symbols = set()
    
    for e in equities:
        base = e.symbol.replace("NSE:", "").replace("BSE:", "").replace("BOM:", "")
        if base in RENAME_MAP:
            new_name = RENAME_MAP[base]["name"]
            print(f"Renaming Equity: {e.symbol} -> {new_name}")
            e.symbol = new_name
            e.scrip_name = new_name
            updated_symbols.add(new_name)
            
    db.commit()
    print(f"Renamed {len(updated_symbols)} unique scrips in Equity table.")
    
    # 2. Update/Sync PriceCache
    for code, info in RENAME_MAP.items():
        name = info["name"]
        yahoo = info["yahoo"]
        
        # Check if an entry for the new name exists
        cache_entry = db.query(PriceCache).filter(PriceCache.symbol == name).first()
        if cache_entry:
            cache_entry.yahoo_symbol = yahoo
            print(f"Updated PriceCache: {name} -> {yahoo}")
        else:
            new_entry = PriceCache(symbol=name, yahoo_symbol=yahoo)
            db.add(new_entry)
            print(f"Created PriceCache: {name} -> {yahoo}")
            
    db.commit()
    
    # 3. Refresh Data for these scrips
    for name in updated_symbols:
        try:
            print(f"\n--- Refreshing {name} ---")
            yahoo = RENAME_MAP.get(next((k for k, v in RENAME_MAP.items() if v["name"] == name), None), {}).get("yahoo")
            
            # Update Price/PE/EPS
            analytics_service.update_analytics(db, name)
            # Update ROE/ROCE
            if yahoo:
                compute_and_store_profitability(db, name, yahoo)
            # Compute Star Rating
            compute_and_store_rating(db, name)
            print(f"Success: {name}")
        except Exception as err:
            print(f"Error refreshing {name}: {err}")
            
    db.close()
    print("\nRename and refresh complete.")

if __name__ == "__main__":
    run_rename()
