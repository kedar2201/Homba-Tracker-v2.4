from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.radar_engine import radar_engine
from ..auth.auth import get_current_user
from ..models.user import User

router = APIRouter(tags=["Radar"])

@router.post("/evaluate")
def trigger_evaluation(db: Session = Depends(get_db)):
    """Manually trigger the evaluation engine for all active users."""
    radar_engine.evaluate_all(db)
    return {"status": "success", "message": "Radar evaluation completed"}

@router.get("/sync-radar")
def refresh_radar(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Refreshes market data and re-evaluates all tracked scrips for the current user."""
    from ..services.analytics import analytics_service
    from ..models.user import Tracklist
    
    # 1. Identity symbols to refresh
    track_items = db.query(Tracklist).filter(Tracklist.user_id == current_user.id).all()
    symbols = list(set([item.symbol for item in track_items]))
    
    if not symbols:
        return {"status": "success", "message": "No scrips in radar to refresh"}
        
    # 2. Update analytics for each
    for symbol in symbols:
        try:
            analytics_service.update_analytics(db, symbol)
        except Exception as e:
            print(f"Error refreshing {symbol}: {e}")
            
    # 3. Trigger radar evaluation specifically for this user
    radar_engine.evaluate_user_radar(db, current_user)
    
    return {"status": "success", "message": f"Refreshed {len(symbols)} scrips and re-evaluated scores"}

@router.get("/signals")
def get_radar_signals(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch historical signals for the current user."""
    from ..models.user import RadarSignalLog
    signals = db.query(RadarSignalLog).filter(RadarSignalLog.user_id == current_user.id).order_by(RadarSignalLog.created_at.desc()).limit(50).all()
    return signals
