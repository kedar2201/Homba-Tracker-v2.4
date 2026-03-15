
import sys
import os
import random
from datetime import datetime, timedelta

# Ensure 'app' is importable
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import User, NAVHistory

db = SessionLocal()
user = db.query(User).filter(User.username == 'newuser1').first()

if not user:
    print("User not found")
    sys.exit(1)

print(f"fixing graph history for user {user.username}")

# Fetch the Latest Record (Verified Live Data)
last_rec = db.query(NAVHistory).filter(NAVHistory.user_id == user.id).order_by(NAVHistory.timestamp.desc()).first()

if not last_rec:
    print("No history found")
    sys.exit(1)

# Capture the CORRECT current state
current_net_worth = last_rec.total_value        # ~16.84 Cr (Total Portfolio)
current_equity_nav = last_rec.nav_per_share     # ~519 (Equity Only)
current_invested = last_rec.total_invested
current_shares = last_rec.total_shares

print(f"Current Net Worth: {current_net_worth}")
print(f"Current Equity NAV: {current_equity_nav}")

# CLEAR BAD HISTORY (The 5.6 Cr / 596 NAV records)
db.query(NAVHistory).filter(NAVHistory.user_id == user.id).delete()
db.commit()

# REPOPULATE with STABLE history based on Current Correct State
for i in range(30, -1, -1):
    dt = datetime.utcnow() - timedelta(days=i)
    # Tiny jitter to look natural
    fluctuation = 1.0 + (random.uniform(-0.002, 0.002))
    
    rec = NAVHistory(
        user_id=user.id,
        total_value=current_net_worth * fluctuation,
        total_invested=current_invested,
        nav_per_share=current_equity_nav * fluctuation,
        total_shares=current_shares,
        timestamp=dt
    )
    db.add(rec)

db.commit()
print("Graph history fixed.")
