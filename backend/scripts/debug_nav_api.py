
from app.database import SessionLocal
from app.models.nav_history import NAVHistory

def check_nav_history():
    db = SessionLocal()
    try:
        # Check latest entry for USER 2
        latest = db.query(NAVHistory).filter(NAVHistory.user_id == 2).order_by(NAVHistory.timestamp.desc()).first()
        if latest:
            print(f"LATEST DB ENTRY (User 2): Date={latest.timestamp} NAV={latest.nav_per_share} TotalVal={latest.total_value}")
        else:
            print("No history found for User 2")
    finally:
        db.close()

if __name__ == "__main__":
    check_nav_history()
