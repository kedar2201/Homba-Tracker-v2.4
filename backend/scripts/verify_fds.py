from app.database import SessionLocal
from app.models.fixed_deposit import FixedDeposit
from app.models.user import User
from datetime import date

db = SessionLocal()
user = db.query(User).filter(User.username == "testuser1").first()
if user:
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == user.id).all()
    today = date.today()
    active_fds = [f for f in fds if f.maturity_date and f.maturity_date >= today]
    matured_fds = [f for f in fds if f.maturity_date and f.maturity_date < today]
    
    total_principal_all = sum(f.principal for f in fds)
    total_principal_active = sum(f.principal for f in active_fds)
    
    print(f"Total FDs in DB: {len(fds)}")
    print(f"Active FDs: {len(active_fds)}")
    print(f"Matured FDs: {len(matured_fds)}")
    print(f"Sum of Principal (All): {total_principal_all}")
    print(f"Sum of Principal (Active Only): {total_principal_active}")
else:
    print("User not found")
db.close()
