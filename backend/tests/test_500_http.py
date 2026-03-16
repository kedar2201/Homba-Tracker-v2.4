import json
import urllib.request
from app.auth.auth import create_access_token
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
for u in db.query(User).all():
    token = create_access_token(data={"sub": u.username})
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/auth/tracklist", headers={"Authorization": f"Bearer {token}"})
        res = urllib.request.urlopen(req)
        print(f"User {u.username} OK: {res.status}")
    except urllib.error.HTTPError as e:
        print(f"User {u.username} FAILED: {e.code}")
        print(e.read().decode())
        
