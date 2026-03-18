from main import app
from app.routers.auth import get_tracklist
from app.database import SessionLocal
from app.models.user import User
from fastapi.encoders import jsonable_encoder
import json
import math

db = SessionLocal()
for u in db.query(User).filter(User.username.in_(['testuser1', 'newuser1'])).all():
    print("Testing", u.username)
    res = get_tracklist(current_user=u, db=db)
    
    # Check for NaN manually
    has_nan = False
    for r in res:
        for k, v in r.items():
            if type(v) is float and math.isnan(v):
                print("FOUND NAN in", k)
                has_nan = True
                
    encoded = jsonable_encoder(res)
    try:
        json.dumps(encoded)
        print("Success for", u.username)
    except Exception as e:
        print("Failed for", u.username, "->", e)
