
from app.database import SessionLocal
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund

def audit_sgb():
    db = SessionLocal()
    try:
        print("--- EQUITY SGBs ---")
        equities = db.query(Equity).all()
        for e in equities:
            name_match = (e.scrip_name and "SGB" in e.scrip_name.upper())
            sym_match = e.symbol.startswith("SGB")
            if name_match or sym_match:
                price = e.current_price or e.buy_price or 0
                val = price * e.quantity
                print(f"EQ: {e.symbol} User:{e.user_id} Name:{e.scrip_name} Qty:{e.quantity} Price:{price} Val:{val} Status:{e.status}")

        print("\n--- MF SGBs ---")
        mfs = db.query(MutualFund).all()
        for m in mfs:
            name_match = "sgb" in m.scheme_name.lower()
            if m.interest_rate and m.interest_rate > 0 or name_match:
                val = 7750.0 * m.units
                print(f"MF: {m.scheme_name} Units:{m.units} Val:{val} Status:{m.status}")

    finally:
        db.close()

if __name__ == "__main__":
    audit_sgb()
