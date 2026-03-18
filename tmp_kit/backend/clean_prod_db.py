
import sys
import os
# Ensure we can import 'app'
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import User, NAVHistory

# Explicitly use backend DB (implied by running in backend dir)
print(f"Current Directory: {os.getcwd()}")
print("Connecting to DB...")

db = SessionLocal()
user = db.query(User).filter(User.username == 'newuser1').first()

if user:
    print(f"Cleaning PROD history for user {user.username} (ID: {user.id})")
    
    # Check if bad records exist
    bad_recs = db.query(NAVHistory).filter(NAVHistory.user_id == user.id, NAVHistory.total_value > 170000000).count()
    print(f"Found {bad_recs} bad records > 17 Cr.")
    
    # Delete points with output > 17 Cr
    deleted_val = db.query(NAVHistory).filter(NAVHistory.user_id == user.id, NAVHistory.total_value > 170000000).delete()
    # Delete points with NAV > 600
    deleted_nav = db.query(NAVHistory).filter(NAVHistory.user_id == user.id, NAVHistory.nav_per_share > 600).delete()
    
    db.commit()
    print(f"Deleted {deleted_val + deleted_nav} records from LIVE DB.")
    
    # Verify
    remaining = db.query(NAVHistory).filter(NAVHistory.user_id == user.id).order_by(NAVHistory.timestamp).all()
    print("\n--- Live History ---")
    for r in remaining:
        print(f"{r.timestamp}: NAV {r.nav_per_share:.2f}, Value {r.total_value:.2f}")

else:
    print("User not found")
db.close()
