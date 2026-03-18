from app.database import SessionLocal
from app.models.nav_history import NAVHistory
import sys

def inspect_db():
    print("--- Inspecting Backend DB NAVHistory ---")
    db = SessionLocal()
    try:
        # Check counts
        count = db.query(NAVHistory).count()
        print(f"Total Entries: {count}")
        
        # Check distribution of values
        # Get first, middle, last
        entries = db.query(NAVHistory).order_by(NAVHistory.timestamp).all()
        if not entries:
            print("No entries found!")
            return
            
        print(f"First: {entries[0].timestamp} - {entries[0].total_value}")
        print(f"Mid:   {entries[len(entries)//2].timestamp} - {entries[len(entries)//2].total_value}")
        print(f"Last:  {entries[-1].timestamp} - {entries[-1].total_value}")
        
        # specific check for 48Cr range
        high_val_count = db.query(NAVHistory).filter(NAVHistory.total_value > 400000000).count() # > 40Cr
        print(f"Entries > 40 Cr: {high_val_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    inspect_db()
