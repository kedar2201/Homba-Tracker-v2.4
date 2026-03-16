import sys
import os

# Set up paths to import app
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user import Tracklist

def update_tracklist_with_quality():
    db = SessionLocal()
    user_id = 1 # Update for testuser1
    
    # First, clear existing tracks for this user to start fresh (or just update)
    # db.query(Tracklist).filter(Tracklist.user_id == user_id).delete()
    
    stock_data = [
        {"symbol": "HDFCBANK.NS",  "sector": "bank",     "roe": 11.6, "nim": 4.1,  "gnpa": 1.2, "roce": 0},
        {"symbol": "SBIN.NS",      "sector": "bank",     "roe": 15.9, "nim": 3.3,  "gnpa": 2.1, "roce": 0},
        {"symbol": "RELIANCE.NS",  "sector": "standard", "roe": 8.8,  "roce": 9.1,  "nim": 0,   "gnpa": 0},
        {"symbol": "TCS.NS",       "sector": "standard", "roe": 49.5, "roce": 60.7, "nim": 0,   "gnpa": 0},
        {"symbol": "INFY.NS",      "sector": "standard", "roe": 30.2, "roce": 37.6, "nim": 0,   "gnpa": 0},
        {"symbol": "MARUTI.NS",    "sector": "standard", "roe": 14.0, "roce": 17.7, "nim": 0,   "gnpa": 0},
        {"symbol": "SUNPHARMA.NS", "sector": "standard", "roe": 15.1, "roce": 17.1, "nim": 0,   "gnpa": 0},
        {"symbol": "TITAN.NS",     "sector": "standard", "roe": 31.1, "roce": 35.5, "nim": 0,   "gnpa": 0},
        {"symbol": "NTPC.NS",      "sector": "standard", "roe": 12.4, "roce": 10.0, "nim": 0,   "gnpa": 0},
        {"symbol": "ASIANPAINT.NS","sector": "standard", "roe": 24.6, "roce": 30.6, "nim": 0,   "gnpa": 0},
        {"symbol": "NEWGEN.NS",    "sector": "standard", "roe": 22.4, "roce": 28.5, "nim": 0,   "gnpa": 0},
    ]

    for data in stock_data:
        # Check if already exists
        track = db.query(Tracklist).filter(Tracklist.user_id == user_id, Tracklist.symbol == data["symbol"]).first()
        if not track:
            print(f"Adding {data['symbol']}...")
            track = Tracklist(
                user_id=user_id,
                symbol=data["symbol"],
                target_price=0,
                sector_type=data["sector"],
                roe=data["roe"],
                roce=data["roce"],
                nim=data.get("nim", 0),
                gnpa=data.get("gnpa", 0),
                dip_percent=8.0,
                rsi_threshold=38.0
            )
            db.add(track)
        else:
            print(f"Updating {data['symbol']}...")
            track.sector_type = data["sector"]
            track.roe = data["roe"]
            track.roce = data["roce"]
            track.nim = data.get("nim", 0)
            track.gnpa = data.get("gnpa", 0)

    db.commit()
    db.close()
    print("Tracklist updated with Model-2Q Quality metrics.")

if __name__ == "__main__":
    update_tracklist_with_quality()
