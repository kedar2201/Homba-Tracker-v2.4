
from app.database import SessionLocal, engine
from app.models.nav_history import NAVHistory
from sqlalchemy import text

def clear_table():
    db = SessionLocal()
    try:
        print("Clearing NAVHistory table...")
        # Try ORM delete
        num = db.query(NAVHistory).delete()
        print(f"Deleted {num} rows via ORM.")
        
        # Try raw SQL truncate/delete just in case
        db.execute(text("DELETE FROM nav_history"))
        db.commit()
        print("Committed delete.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_table()
