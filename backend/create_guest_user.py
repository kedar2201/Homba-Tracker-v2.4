import sys
import os
# Add the project root to the python path
sys.path.append(os.getcwd())

from backend.app.models.user import User
from backend.app.auth.auth import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_guest():
    # Force connection to backend DB
    db_path = os.path.join(os.getcwd(), 'backend', 'financial_portfolio.db')
    print(f"Connecting to: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        username = "guest"
        password = "guest123"
        
        user = db.query(User).filter(User.username == username).first()
        if user:
            print(f"User '{username}' already exists.")
            # Update password just in case
            user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"Password reset to '{password}'.")
        else:
            print(f"Creating user '{username}'...")
            hashed_password = get_password_hash(password)
            new_user = User(email="guest@example.com", username=username, hashed_password=hashed_password)
            db.add(new_user)
            db.commit()
            print(f"User '{username}' created successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_guest()
