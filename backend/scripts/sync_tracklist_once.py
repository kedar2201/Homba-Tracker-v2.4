import logging
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user import Tracklist
from app.models.market_data import PriceCache
from app.services.analytics import analytics_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_tracklist():
    db = SessionLocal()
    try:
        # Get all unique symbols from all users' tracklists
        symbols = [row[0] for row in db.query(Tracklist.symbol).distinct().all()]
        logger.info(f"Syncing {len(symbols)} symbols from tracklists: {symbols}")
        
        for symbol in symbols:
            # Ensure PriceCache exists
            entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
            if not entry:
                logger.info(f"Creating PriceCache entry for {symbol}")
                entry = PriceCache(symbol=symbol)
                db.add(entry)
                db.commit()
            
            # Update analytics (Price, MA, EPS, etc)
            logger.info(f"Updating analytics for {symbol}...")
            try:
                # Force a refresh
                res = analytics_service.update_analytics(db, symbol)
                if res and res.price:
                    logger.info(f"Successfully updated {symbol}: Price={res.price}")
                else:
                    logger.warning(f"Updated {symbol} but price is still missing.")
            except Exception as e:
                logger.error(f"Failed to update {symbol}: {e}")
                
        db.commit()
        logger.info("Tracklist sync complete.")
    finally:
        db.close()

if __name__ == "__main__":
    sync_tracklist()
