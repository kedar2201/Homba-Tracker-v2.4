from app.database import SessionLocal
from app.models.equity import Equity, EquityStatus

def verify_migration():
    db = SessionLocal()
    try:
        e = db.query(Equity).first()
        if e:
            print(f"Equity {e.symbol} current status: {e.status}")
            e.status = EquityStatus.ACTIVE
            db.commit()
            print("Successfully updated status to ACTIVE and committed.")
        else:
            print("No equities to test, but query succeeded.")
    except Exception as e:
        print(f"Migration verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_migration()
