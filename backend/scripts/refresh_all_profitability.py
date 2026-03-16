from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.services.profitability_service import compute_and_store_profitability
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def refresh_all(force=False):
    db = SessionLocal()
    try:
        # All scrips with a yahoo mapping
        query = db.query(PriceCache).filter(PriceCache.yahoo_symbol != None)
        entries = query.all()
            
        print(f"Found {len(entries)} scrips to refresh profitability for.")
        
        success_count = 0
        error_count = 0
        
        for i, entry in enumerate(entries):
            symbol = entry.symbol
            ticker = entry.yahoo_symbol
            print(f"[{i+1}/{len(entries)}] Refreshing Profitability for {symbol} (Ticker: {ticker})...")
            
            try:
                compute_and_store_profitability(db, symbol, ticker)
                success_count += 1
                # Commit frequently to release locks
                if success_count % 10 == 0:
                    db.commit()
            except Exception as e:
                print(f"  Error refreshing {symbol}: {e}")
                error_count += 1
        
        db.commit()
        print(f"\nRefresh complete. Success: {success_count}, Errors: {error_count}")

    finally:
        db.close()

if __name__ == "__main__":
    refresh_all()
