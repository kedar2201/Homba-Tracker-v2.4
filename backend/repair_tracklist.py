from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import Tracklist
from app.models.market_data import PriceCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_tracklist_fundamentals():
    db = SessionLocal()
    try:
        items = db.query(Tracklist).all()
        logger.info(f"Checking {len(items)} tracklist items...")
        
        updated_count = 0
        for item in items:
            # If fundamentals are zero/empty, try to pull from PriceCache
            if (item.roe == 0 or item.roe is None) and (item.nim == 0 or item.nim is None):
                cache = db.query(PriceCache).filter(PriceCache.symbol == item.symbol).first()
                if cache:
                    logger.info(f"Syncing {item.symbol} from cache...")
                    item.roe = cache.roe or 0.0
                    item.roce = cache.roce or 0.0
                    item.nim = cache.nim
                    item.gnpa = cache.gnpa
                    item.ev_growth = cache.ev_growth
                    item.solvency_ratio = cache.solvency_ratio
                    updated_count += 1
        
        db.commit()
        logger.info(f"Successfully repaired {updated_count} items.")
    finally:
        db.close()

if __name__ == "__main__":
    repair_tracklist_fundamentals()
