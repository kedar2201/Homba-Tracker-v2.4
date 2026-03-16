
from app.database import SessionLocal
from app.models.equity import Equity

def get_user2_units():
    db = SessionLocal()
    try:
        equities = db.query(Equity).filter(Equity.user_id == 2).all()
        buy_units = sum(e.buy_units or 0 for e in equities)
        sell_units = sum(e.sell_units or 0 for e in equities)
        net_units = buy_units - sell_units
        print(f"USER 2 Net Equity Units: {net_units}")
    finally:
        db.close()

if __name__ == "__main__":
    get_user2_units()
