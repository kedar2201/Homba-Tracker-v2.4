import sys
import traceback
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.routers.auth import get_tracklist, get_radar_config
from app.models.user import User
from app.schemas.user import TracklistSchema, RadarScoringSchema
from pydantic import TypeAdapter

db = SessionLocal()

for user in db.query(User).all():
    try:
        results = get_tracklist(current_user=user, db=db)
        TypeAdapter(list[TracklistSchema]).validate_python(results)
    except Exception as e:
        print(f"Tracklist failed for user {user.id} ({user.username}):", e)

    try:
        config = get_radar_config(current_user=user, db=db)
        RadarScoringSchema.model_validate(config)
    except Exception as e:
        print(f"Config failed for user {user.id} ({user.username}):", e)

print("Done validating all.")
