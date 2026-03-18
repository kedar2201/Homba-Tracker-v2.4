import sys
import traceback
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.routers.auth import get_tracklist
from app.models.user import User

db = SessionLocal()
# The main user is probably ID 1 or the one the user is using.
user = db.query(User).filter(User.id == 1).first()

try:
    res = get_tracklist(current_user=user, db=db)
    print("Success for user 1!")
except Exception as e:
    print("Error for user 1:")
    traceback.print_exc()

user2 = db.query(User).filter(User.id == 2).first()
try:
    res = get_tracklist(current_user=user2, db=db)
    print("Success for user 2!")
except Exception as e:
    print("Error for user 2:")
    traceback.print_exc()
