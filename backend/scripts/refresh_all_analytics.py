import sys
import os
import time
import logging
from sqlalchemy.orm import Session

# Add current dir to path to import app
sys.path.insert(0, os.getcwd())
from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.services.analytics import analytics_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def refresh_all(force=False):
    db = SessionLocal()
    try:
        # Get all entries with a yahoo symbol
        query = db.query(PriceCache).filter(PriceCache.yahoo_symbol != None)
        
        if not force:
            # Filter for those missing mandatory metrics
            symbols = [r.symbol for r in query.filter(
                (PriceCache.pe == None) | 
                (PriceCache.eps == None) | 
                (PriceCache.ma50 == None) |
                (PriceCache.price == None)
            ).all()]
        else:
            symbols = [r.symbol for r in query.all()]
            
        print(f"Found {len(symbols)} scrips to refresh.")
        
        success_count = 0
        error_count = 0
        
        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] Refreshing {symbol}...")
            
            try:
                # Use the existing service logic which we just refactored to use the mapping
                updated = analytics_service.update_analytics(db, symbol)
                if updated:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"  Error refreshing {symbol}: {e}")
                error_count += 1
                db.rollback()
            
            # Small delay to be polite to Yahoo Finance
            time.sleep(1.0)
            
            # Periodically recreate session if it's a huge batch to avoid memory/lock issues
            if i % 20 == 0 and i > 0:
                db.close()
                db = SessionLocal()

        print(f"\nRefresh complete. Success: {success_count}, Errors: {error_count}")

    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Refresh all mapped scrips, not just incomplete ones")
    args = parser.parse_args()
    
    refresh_all(force=args.force)
