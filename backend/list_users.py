import sys
import os
# Ensure the current directory is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User

def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        print("-" * 50)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30}")
        print("-" * 50)
        for u in users:
            print(f"{u.id:<5} {u.username:<20} {u.email:<30}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_users()
