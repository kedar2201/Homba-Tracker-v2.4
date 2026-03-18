from app.database import SessionLocal
from app.models.user import User
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund
from app.models.fixed_deposit import FixedDeposit
from app.models.other_asset import OtherAsset
from app.routers.dashboard import get_dashboard_summary

db = SessionLocal()
u = db.query(User).filter(User.username == 'newuser1').first()

if u:
    print(f"=== DETAILED INSPECTOR FOR {u.username} ===")
    
    # Check Equities
    eqs = db.query(Equity).filter(Equity.user_id == u.id).all()
    print(f"\nEquities ({len(eqs)}):")
    for e in eqs:
        is_sgb = e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper())
        price = e.current_price or e.buy_price or 0
        val = price * e.quantity
        print(f"  {e.symbol} | Qty: {e.quantity} | P: {price} | V: {val} | SGB: {is_sgb}")
        
    # Check MFs
    mfs = db.query(MutualFund).filter(MutualFund.user_id == u.id).all()
    print(f"\nMutual Funds ({len(mfs)}):")
    for m in mfs:
        is_sgb = m.interest_rate and m.interest_rate > 0 or "sgb" in m.scheme_name.lower()
        print(f"  {m.scheme_name} | Units: {m.units} | Invested: {m.invested_amount} | SGB: {is_sgb}")

    # Check Summary
    s = get_dashboard_summary(current_user=u, db=db)
    print(f"\nDashboard Summary Metrics:")
    for k, v in s.items():
        if isinstance(v, (int, float)):
            print(f"  {k}: {v}")
db.close()
