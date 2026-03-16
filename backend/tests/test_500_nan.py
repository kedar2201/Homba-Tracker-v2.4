import json, math
from app.database import SessionLocal
from app.routers.auth import get_tracklist
from app.models.user import User

db = SessionLocal()
for u in db.query(User).all():
    if u.username in ['testuser1', 'newuser1']:
        res = get_tracklist(current_user=u, db=db)
        for d in res:
            for k, v in d.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    print(f"User {u.username}, Item {d.get('symbol')} has {k} = {v}")
