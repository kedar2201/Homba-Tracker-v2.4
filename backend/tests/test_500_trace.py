from fastapi.testclient import TestClient
from app.main import app
from app.auth.auth import create_access_token
from app.database import SessionLocal
from app.models.user import User
import sys, traceback

client = TestClient(app)
db = SessionLocal()

u = db.query(User).filter(User.username == 'testuser1').first()
token = create_access_token(data={"sub": u.username})

try:
    response = client.get("/api/auth/tracklist", headers={"Authorization": f"Bearer {token}"})
    print(response.status_code)
    print(response.json())
except Exception as e:
    traceback.print_exc()
