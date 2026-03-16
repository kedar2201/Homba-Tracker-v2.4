import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routers.dashboard import get_growth_analysis
from app.database import SessionLocal
from app.models.user import User

def verify():
    print("--- Verify Growth Analysis Internal ---")
    try:
        db = SessionLocal()
        user = User(id=1, email="test@test.com")
        
        print("Calling get_growth_analysis...")
        data = get_growth_analysis(current_user=user, db=db)
        
        if not data:
            print("FAILURE: No data returned")
            return
            
        print(f"Returned {len(data)} records")
        last = data[-1]
        print(f"Last Record Date: {last['date']}")
        print(f"Last Portfolio Value: {last['portfolio_val']}")
        print(f"Last NAV: {last['nav']}")
        
        if last['portfolio_val'] > 150000000: # > 15 Cr
            print("SUCCESS: Magnitude correct (> 15Cr)")
        else:
            print(f"FAILURE: Magnitude too low ({last['portfolio_val']})")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
