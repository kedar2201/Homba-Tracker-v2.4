from app.database import SessionLocal
from app.models.user import User
from app.routers.dashboard import get_dashboard_summary

db = SessionLocal()
u = db.query(User).filter(User.username == 'newuser1').first()
if u:
    s = get_dashboard_summary(current_user=u, db=db)
    print(f'Breakdown for {u.username}:')
    print(f'  Equity: {s.get("equity")}')
    print(f'  MF:     {s.get("mf")}')
    print(f'  FD:     {s.get("fd")}')
    print(f'  Bonds:  {s.get("bonds")}')
    print(f'  Liquid: {s.get("liquidable_assets")}')
    print(f'  Other:  {s.get("other")}')
    print(f'  Total:  {s.get("total")}')
    print(f'  Eq Port NAV: {s.get("equity_portfolio_nav")}')
db.close()
