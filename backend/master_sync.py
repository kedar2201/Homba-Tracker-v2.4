from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import Tracklist
from app.models.market_data import PriceCache
from app.services.analytics import analytics_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def master_sync():
    db = SessionLocal()
    try:
        # 1. Get all unique symbols
        items = db.query(Tracklist).all()
        symbols = list(set([item.symbol for item in items]))
        logger.info(f"Master Sync for {len(symbols)} symbols: {symbols}")
        
        for s in symbols:
            try:
                # Force refresh in PriceCache
                logger.info(f"Syncing {s}...")
                analytics_service.update_analytics(db, s)
                
                # Verify
                p = db.query(PriceCache).filter(PriceCache.symbol == s).first()
                if p:
                    logger.info(f"Result for {s}: ROE={p.roe}, ROCE={p.roce}, PE={p.pe}")
            except Exception as e:
                logger.error(f"Failed to sync {s}: {e}")
        
        db.commit()
        logger.info("Master Sync Completed.")
    finally:
        db.close()

if __name__ == "__main__":
    master_sync()
