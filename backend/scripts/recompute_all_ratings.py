import sys
import os
import logging
from sqlalchemy.orm import Session

# Add current dir to path to import app
sys.path.insert(0, os.getcwd())
from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.services.rating_engine import compute_and_store_rating

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recompute_all():
    db = SessionLocal()
    try:
        # Get all unique symbols from PriceCache (the base list for our ratings)
        symbols = [r.symbol for r in db.query(PriceCache.symbol).all()]
        
        print(f"Found {len(symbols)} scrips to recompute rating for.")
        
        rated_count = 0
        skipped_count = 0
        
        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] Rating {symbol}...", end="\r")
            
            try:
                # Full pipeline: check readiness -> score -> store
                result = compute_and_store_rating(db, symbol)
                if result.get("state") == "RATED":
                    rated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"\n  Error rating {symbol}: {e}")
                db.rollback()
            
            # Periodically recreate session to avoid cache/lock issues
            if i % 50 == 0 and i > 0:
                db.close()
                db = SessionLocal()

        print(f"\n\nRecompute complete.")
        print(f"RATED:   {rated_count}")
        print(f"SKIPPED: {skipped_count} (Mandatory data missing)")

    finally:
        db.close()

if __name__ == "__main__":
    recompute_all()
