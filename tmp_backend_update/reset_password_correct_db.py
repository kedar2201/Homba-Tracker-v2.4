import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User  # This requires 'app' module to be importable
from app.auth.auth import get_password_hash

# Ensure the backend directory is in the python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

# The correct database file is likely one level UP from 'backend'
# Or potentially inside 'backend' depending on how uvicorn was started.
# Let's check both or target the one the main app uses.

# Assuming main app runs from 'financial_portfolio_tracker' root:
root_dir = os.path.dirname(backend_dir)
db_path_root = os.path.join(root_dir, "financial_portfolio.db")
db_path_backend = os.path.join(backend_dir, "financial_portfolio.db")

target_db_url = f"sqlite:///{db_path_root}"

print(f"Targeting Database: {target_db_url}")

engine = create_engine(target_db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reset_password(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' NOT FOUND in {target_db_url}")
            # Try the backend folder one just in case
            if os.path.exists(db_path_backend):
                 print(f"Checking alternative DB at {db_path_backend}...")
                 # Logic for checking secondary DB could go here but let's stick to the main one first.
        else:
            print(f"Found user '{username}'. ID: {user.id}")
            print(f"Resetting password...")
            user.hashed_password = get_password_hash("password123")
            db.commit()
            print(f"Success! Password for '{username}' set to 'password123' in {target_db_url}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        reset_password(sys.argv[1])
    else:
        reset_password("newuser1")
