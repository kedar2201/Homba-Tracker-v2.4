import sys
import os
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add current dir to path to import app.database
sys.path.insert(0, os.getcwd())
from app.database import SessionLocal, engine
from app.models.equity import Equity, Exchange
from app.models.market_data import PriceCache
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

def validate_ticker(ticker):
    """Check if ticker returns valid info from Yahoo."""
    try:
        t = yf.Ticker(ticker)
        # history(period='1d') is a definitive check
        hist = t.history(period='1d')
        if not hist.empty:
            return True
        return False
    except Exception:
        return False

def populate():
    db = SessionLocal()
    try:
        # 1. Get all unique symbols from PriceCache
        rows = db.query(PriceCache).all()
        print(f"Found {len(rows)} symbols in PriceCache to map.")

        updated_count = 0
        batch_size = 5
        for i, pc in enumerate(rows):
            if pc.yahoo_symbol and pc.yahoo_symbol_locked:
                continue
            
            raw_symbol = pc.symbol
            # CLEAN symbol: More robust stripping
            symbol = raw_symbol
            if ":" in symbol:
                symbol = symbol.split(":")[-1].strip()
            
            # Skip common prefixes if they somehow persisted in cleanup
            for pref in ["NSE", "BSE", "BOM"]:
                if symbol.startswith(f"{pref}:"):
                    symbol = symbol.split(":")[-1].strip()

            # Skip indices but store correctly
            if raw_symbol.startswith("^"):
                pc.yahoo_symbol = raw_symbol
                continue

            # Check if we have an exchange in equities table
            eq = db.query(Equity).filter(Equity.symbol == raw_symbol).first()
            exchange = eq.exchange if eq else None
            
            candidates = []
            
            # If it already has a suffix, try that first
            if "." in symbol:
                candidates.append(symbol)
                
            if exchange == Exchange.NSE:
                candidates.append(f"{symbol}.NS")
            elif exchange == Exchange.BSE:
                candidates.append(f"{symbol}.BO")
            
            # Guesses and fallbacks
            if symbol.isdigit():
                if f"{symbol}.BO" not in candidates: candidates.append(f"{symbol}.BO")
                if f"{symbol}.NS" not in candidates: candidates.append(f"{symbol}.NS")
            else:
                if f"{symbol}.NS" not in candidates: candidates.append(f"{symbol}.NS")
                if f"{symbol}.BO" not in candidates: candidates.append(f"{symbol}.BO")
                # Absolute raw (for US stocks)
                if symbol not in candidates: candidates.append(symbol)
            
            found_symbol = None
            for cand in candidates:
                print(f"  [{i+1}/{len(rows)}] Validating {cand:15} for {raw_symbol:12}...", end="\r")
                if validate_ticker(cand):
                    found_symbol = cand
                    break
            
            if found_symbol:
                pc.yahoo_symbol = found_symbol
                updated_count += 1
                # Also update all equities with this symbol
                db.execute(
                    text("UPDATE equities SET yahoo_symbol = :ys WHERE symbol = :sym AND (yahoo_symbol_locked = 0 OR yahoo_symbol_locked IS NULL)"),
                    {"ys": found_symbol, "sym": raw_symbol}
                )
                print(f"  [{i+1}/{len(rows)}] Mapped {raw_symbol:12} -> {found_symbol:14} [VALID]")
                
                # Commit in batches to release locks
                if updated_count % batch_size == 0:
                    try:
                        db.commit()
                    except Exception as e:
                        print(f"  Error committing batch: {e}")
                        db.rollback()
            else:
                print(f"  [{i+1}/{len(rows)}] Mapped {raw_symbol:12} -> FAILED                ")

        db.commit()
        print(f"\nAuto-population complete. Updated {updated_count} symbols.")

    finally:
        db.close()

if __name__ == "__main__":
    populate()
