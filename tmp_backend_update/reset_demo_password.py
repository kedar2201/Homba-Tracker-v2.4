import sys
import os

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.auth.auth import get_password_hash

def reset_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "demo").first()
        if not user:
            print("User 'demo' not found. Creating it...")
            hashed_password = get_password_hash("password123")
            user = User(username="demo", email="demo@example.com", hashed_password=hashed_password)
            db.add(user)
        else:
            print("Resetting password for user 'demo'...")
            user.hashed_password = get_password_hash("password123")
        
        db.commit()
        print("Success! Login with username: 'demo' and password: 'password123'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_password()
