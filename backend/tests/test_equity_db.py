import requests

def test_equity_get():
    # We need a token. Let's just try to call it and see if we get a 500 or just a 401.
    # But a better way is to mock the DB call.
    pass

if __name__ == "__main__":
    # Test internal logic
    from app.database import SessionLocal
    from app.models.equity import Equity
    from app.auth.auth import get_current_user
    
    db = SessionLocal()
    try:
        # Just try to fetch all equities to see if it even works
        eqs = db.query(Equity).all()
        print(f"Fetched {len(eqs)} equities successfully.")
        for eq in eqs[:1]:
            print(f"Sample: {eq.symbol}, {eq.exchange}, {eq.instrument_type}")
    except Exception as e:
        print(f"ERROR FETCHING EQUITIES: {e}")
    finally:
        db.close()
