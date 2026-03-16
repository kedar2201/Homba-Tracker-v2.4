from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.models.equity import Equity
from sqlalchemy import text
from app.services.analytics import analytics_service
from app.services.rating_engine import compute_and_store_rating

def fix_bel():
    db = SessionLocal()
    try:
        symbol = 'NSE:BEL'
        yahoo_symbol = 'BEL.NS'
        
        print(f"Locking {symbol} -> {yahoo_symbol}...")
        
        # Update PriceCache
        pc = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
        if pc:
            pc.yahoo_symbol = yahoo_symbol
            pc.yahoo_symbol_locked = True
        
        # Update Equities
        db.execute(
            text("UPDATE equities SET yahoo_symbol = :ys, yahoo_symbol_locked = 1 WHERE symbol = :sym"),
            {"ys": yahoo_symbol, "sym": symbol}
        )
        
        # Cleanup redundant symbols
        db.execute(text("DELETE FROM price_cache WHERE symbol = 'NSE:NSE:BEL'"))
        db.execute(text("DELETE FROM equities WHERE symbol = 'NSE:NSE:BEL'"))
        
        db.commit()
        
        print(f"Refreshing analytics and rating for {symbol}...")
        analytics_service.update_analytics(db, symbol)
        compute_and_store_rating(db, symbol)
        db.commit()
        
        print("Done.")
    finally:
        db.close()

if __name__ == "__main__":
    fix_bel()
