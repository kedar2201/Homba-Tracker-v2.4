from app.database import SessionLocal
from app.models.user import User
from app.auth.auth import get_password_hash

db = SessionLocal()
username = "testuser1"
user = db.query(User).filter(User.username == username).first()

if user:
    print(f"Resetting password for {username}...")
    user.hashed_password = get_password_hash("password123")
    db.commit()
    print("Password reset to 'password123' successfully.")
else:
    print(f"User {username} not found.")

db.close()
