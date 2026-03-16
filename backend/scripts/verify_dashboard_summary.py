import requests

# Assuming the backend is running on localhost:8000
BASE_URL = "http://127.0.0.1:8000"

def verify_summary():
    # We need a token if it's protected. But I'll try to use a direct DB check 
    # if I can't reach the API easily without auth.
    pass

if __name__ == "__main__":
    # Instead of API, let's just run a small script that uses the session directly
    from app.database import SessionLocal
    from app.models.user import User
    from app.routers.dashboard import get_dashboard_summary
    
    db = SessionLocal()
    try:
        # Get the first user or a specific user if known
        user = db.query(User).first()
        if user:
            print(f"Verifying for user: {user.email}")
            summary = get_dashboard_summary(current_user=user, db=db)
            print("Summary Response:")
            import json
            print(json.dumps(summary, indent=4))
        else:
            print("No users found in DB")
    finally:
        db.close()
