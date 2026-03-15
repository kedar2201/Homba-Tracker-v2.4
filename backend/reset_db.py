from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.auth.auth import get_password_hash
from app.models.equity import Equity
from app.models.fixed_deposit import FixedDeposit
from app.models.mutual_fund import MutualFund
from datetime import date

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Create User
    hashed_pwd = get_password_hash("password123")
    user = User(username="testuser1", email="test@example.com", hashed_password=hashed_pwd)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Add Equity
    e1 = Equity(user_id=user.id, exchange="NSE", symbol="RELIANCE", quantity=10, buy_price=2400.0, buy_date=date(2023, 1, 10))
    e2 = Equity(user_id=user.id, exchange="NSE", symbol="TCS", quantity=5, buy_price=3200.0, buy_date=date(2023, 2, 15))
    db.add_all([e1, e2])
    
    # Add MF
    m1 = MutualFund(user_id=user.id, scheme_name="HDFC Top 100", isin="INF209K01157", units=100.0, invested_amount=50000.0, transaction_date=date(2023, 1, 1))
    db.add(m1)
    
    # Add FD
    from app.models.fixed_deposit import CompoundingFrequency, PayoutType
    f1 = FixedDeposit(
        user_id=user.id, 
        bank_name="HDFC Bank", 
        fd_code="FD001", 
        principal=100000.0, 
        interest_rate=7.5, 
        start_date=date(2023, 1, 1), 
        maturity_date=date(2024, 1, 1),
        compounding_frequency=CompoundingFrequency.QUARTERLY,
        payout_type=PayoutType.CUMULATIVE
    )
    db.add(f1)
    
    db.commit()
    print("Database Reset and Seeded with testuser1 / password123")
    db.close()

if __name__ == "__main__":
    reset_db()
