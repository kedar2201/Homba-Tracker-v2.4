from app.database import SessionLocal
from app.routers.dashboard import get_growth_analysis
from app.models.user import User

def test_growth():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("No user found in DB")
            return
        
        print(f"Testing growth for user: {user.username} (id: {user.id})")
        growth = get_growth_analysis(current_user=user, db=db)
        print("Growth retrieved successfully:")
        print(f"Length: {len(growth)}")
        if growth:
            print("First entry:", growth[0])
    except Exception as e:
        print(f"Error retrieving growth: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_growth()
