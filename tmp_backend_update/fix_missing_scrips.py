import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.services.analytics import analytics_service
from app.services.rating_engine import compute_and_store_rating
from app.services.profitability_service import compute_and_store_profitability

SCRIP_MAPS = {
    "PAYTM": "PAYTM.NS",
    "CAMLINFINE": "CAMLINFINE.NS",
    "HINDWAREAP": "HINDWAREAP.NS",
    "BEL": "BEL.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "IDEA": "IDEA.NS",
    "EUREKAFORB": "EUREKAFORB.NS",
    "TIMEX": "TIMEXWATCH.NS",
    "TIMEXWATCH": "TIMEXWATCH.NS",
    "ZFCVINDIA": "ZFCVINDIA.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "EXPLEOSOL": "EXPLEOSOL.NS",
    "ASHIANA": "ASHIANA.NS"
}

def fix_scrips():
    db = SessionLocal()
    
    # 1. Clear double prefixes
    print("Cleaning up double prefixes...")
    db.execute(text("DELETE FROM price_cache WHERE symbol LIKE 'NSE:NSE:%'"))
    db.commit()
    
    symbols_to_fix = list(SCRIP_MAPS.keys())
    # Add variations with NSE: prefix
    all_targets = symbols_to_fix + [f"NSE:{s}" for s in symbols_to_fix]
    
    entries = db.query(PriceCache).filter(PriceCache.symbol.in_(all_targets)).all()
    print(f"Found {len(entries)} entries to update mapping for.")
    
    mapped_symbols = [e.symbol for e in entries]
    
    for entry in entries:
        base = entry.symbol.replace("NSE:", "")
        if base in SCRIP_MAPS:
            entry.yahoo_symbol = SCRIP_MAPS[base]
            print(f"Mapped {entry.symbol} -> {entry.yahoo_symbol}")
    
    # Handle missing IDEA if not in entries
    if not any(e.symbol == "IDEA" for e in entries):
        new_idea = PriceCache(symbol="IDEA", yahoo_symbol="IDEA.NS")
        db.add(new_idea)
        print("Added new entry for IDEA")
        all_targets.append("IDEA")
        
    db.commit()
    
    # 2. Refresh Analytics & Profitability
    fresh_entries = db.query(PriceCache).filter(PriceCache.symbol.in_(all_targets)).all()
    for entry in fresh_entries:
        try:
            print(f"\n--- Refreshing {entry.symbol} (Ticker: {entry.yahoo_symbol}) ---")
            # Update Price/PE/EPS
            analytics_service.update_analytics(db, entry.symbol)
            # Update ROE/ROCE
            compute_and_store_profitability(db, entry.symbol, entry.yahoo_symbol)
            # Compute Star Rating
            compute_and_store_rating(db, entry.symbol)
            print(f"Success: {entry.symbol}")
        except Exception as e:
            print(f"Error refreshing {entry.symbol}: {e}")
            
    db.close()

if __name__ == "__main__":
    fix_scrips()
