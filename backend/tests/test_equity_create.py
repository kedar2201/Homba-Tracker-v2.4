from app.database import SessionLocal
from app.models.equity import Equity, Exchange
from datetime import date

def test_create_equity():
    db = SessionLocal()
    try:
        # Data from user screenshot
        new_equity = Equity(
            user_id=1,  # Assuming user_id 1 exists for testing
            exchange=Exchange.NSE,
            symbol="SGBSEP31III GB",
            scrip_name="SGBSEP31III GB",
            instrument_type="Other",
            quantity=255,
            buy_price=5873.0,
            buy_date=date(2024, 7, 12),
            holder="MANISHA",
            isin="",
            broker="Zerodha"
        )
        db.add(new_equity)
        db.commit()
        db.refresh(new_equity)
        print(f"Successfully created equity with ID: {new_equity.id}")
        
        # Cleanup
        db.delete(new_equity)
        db.commit()
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"FAILED to create equity: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_create_equity()
