import sys
import os
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.market_data import PriceCache
import json

def check_newgen():
    db = SessionLocal()
    # Check for both "NEWGEN" and "NEWGEN.NS"
    for s in ["NEWGEN", "NEWGEN.NS"]:
        entry = db.query(PriceCache).filter(PriceCache.symbol == s).first()
        if entry:
            data = {
                "symbol": entry.symbol,
                "price": entry.price,
                "roe": entry.roe,
                "roce": entry.roce,
                "pe": entry.pe,
                "pe_avg_5y": entry.pe_avg_5y,
                "peg_ratio": entry.peg_ratio,
                "nim": entry.nim,
                "gnpa": entry.gnpa,
                "ev_growth": entry.ev_growth
            }
            print(f"Database Record for {s}:")
            print(json.dumps(data, indent=2))
        else:
            print(f"{s} not found in DB")
    
    # Try calling the logic in Auth.py if possible, or just similar logic
    import yfinance as yf
    s = "NEWGEN"
    ticker = yf.Ticker(f"{s}.NS")
    info = ticker.info
    print("\nYahoo Finance Live Data for NEWGEN.NS:")
    print(f"returnOnEquity: {info.get('returnOnEquity')}")
    print(f"returnOnAssets: {info.get('returnOnAssets')}")
    print(f"pegRatio: {info.get('pegRatio')}")
    print(f"trailingPE: {info.get('trailingPE')}")

if __name__ == "__main__":
    check_newgen()
