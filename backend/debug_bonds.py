
from app.database import SessionLocal
# Assuming Bond model exists, need to find where it is defined since I didn't see it in dashboard imports
# But dashboard screen shows Bonds(2).
# Let's try to import from standard location or check models dir.
from app.models.bond import Bond

def check_bonds():
    db = SessionLocal()
    try:
        bonds = db.query(Bond).filter(Bond.user_id == 1).all()
        print(f"Total Bonds in DB: {len(bonds)}")
        
        total_val = 0
        for b in bonds:
            print(f"Bond: {b.name} | Invested: {b.invested_amount} | Current: {b.current_value}")
            total_val += (b.current_value or b.invested_amount or 0)
            
        print(f"Total Bond Value: {total_val}")
    except Exception as e:
        print(f"Error: {e}")
        # Maybe Bond model is named differently
    finally:
        db.close()

if __name__ == "__main__":
    check_bonds()
