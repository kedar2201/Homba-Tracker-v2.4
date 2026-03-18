import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.auth.auth import get_password_hash


# Assuming the script runs in 'backend/', the root DB is at '../financial_portfolio.db'
# We must use an absolute path for SQLite to be sure.
base_dir = os.path.dirname(os.path.abspath(__file__))
root_db_path = os.path.join(os.path.dirname(base_dir), "financial_portfolio.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{root_db_path}"

# SQLite specific args
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reset_password(username):
    print(f"Connecting to database at: {root_db_path}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' NOT FOUND in {root_db_path}!")
        else:
            print(f"Resetting password for user '{username}' (ID: {user.id})...")
            user.hashed_password = get_password_hash("password123")
            db.commit()
            print(f"Success! Login with username: '{username}' and password: 'password123'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_password("newuser1")
