import json
from datetime import date
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.fixed_deposit import FixedDeposit
from app.routers.fixed_deposit import get_fds
from app.models.user import User

db = SessionLocal()
try:
    # Mock user - just get the first one for testing
    user = db.query(User).first()
    if user:
        result = get_fds(fy_year=2024, db=db, current_user=user)
        print("Success")
        print(f"Results count: {len(result)}")
    else:
        print("No user found")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
