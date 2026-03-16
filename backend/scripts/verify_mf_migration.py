from app.database import SessionLocal
from app.models.mutual_fund import MutualFund, MFStatus

def verify_mf_migration():
    db = SessionLocal()
    try:
        m = db.query(MutualFund).first()
        if m:
            print(f"Mutual Fund {m.scheme_name} current status: {m.status}")
            m.status = MFStatus.ACTIVE
            db.commit()
            print("Successfully updated MF status to ACTIVE and committed.")
        else:
            print("No mutual funds to test, but query succeeded.")
    except Exception as e:
        print(f"MF Migration verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_mf_migration()
