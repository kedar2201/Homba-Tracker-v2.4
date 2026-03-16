from app.database import SessionLocal
from app.routers.dashboard import get_dashboard_summary
from app.models.user import User

def test_summary():
    db = SessionLocal()
    try:
        # Mocking current_user - assuming user_id 1 exists
        user = db.query(User).first()
        if not user:
            print("No user found in DB")
            return
        
        print(f"Testing summary for user: {user.username} (id: {user.id})")
        summary = get_dashboard_summary(current_user=user, db=db)
        print("Summary retrieved successfully:")
        print(summary)
    except Exception as e:
        print(f"Error retrieving summary: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_summary()
