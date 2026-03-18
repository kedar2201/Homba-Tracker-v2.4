import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user import User, Notification
from ..models.equity import Equity

logger = logging.getLogger(__name__)

def generate_daily_portfolio_summaries():
    """
    Background task to calculate P/L for all users and generate notifications.
    Triggered at 3:45 PM (Market Close + 15 mins).
    """
    logger.info("[NotificationService] Starting daily portfolio summary generation...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            try:
                generate_user_summary(db, user)
            except Exception as e:
                logger.error(f"Failed to generate summary for user {user.username}: {e}")
                
        db.commit()
        logger.info(f"[NotificationService] Completed summaries for {len(users)} users.")
    finally:
        db.close()

def generate_user_summary(db: Session, user: User):
    """Calculate specific daily P/L for one user and store notification."""
    # 1. Calculate Equity Daily Gain
    equities = db.query(Equity).filter(Equity.user_id == user.id, Equity.status == "ACTIVE").all()
    
    total_market_value = 0
    total_daily_gain = 0
    
    for eq in equities:
        current_price = eq.current_price or 0
        prev_close = eq.prev_close or current_price
        
        market_value = current_price * eq.quantity
        daily_gain = (current_price - prev_close) * eq.quantity
        
        total_market_value += market_value
        total_daily_gain += daily_gain
        
    if total_market_value == 0:
        return

    # 2. Prepare Notification Message
    gain_arrow = "▲" if total_daily_gain >= 0 else "▼"
    prev_value = total_market_value - total_daily_gain
    gain_pct = (total_daily_gain / prev_value * 100) if prev_value > 0 else 0
    
    title = f"Market Close Report {datetime.now().strftime('%d %b')}"
    message = (
        f"Hi {user.username}, your portfolio closed at \u20b9{total_market_value:,.2f}. "
        f"Daily Movement: {gain_arrow} \u20b9{abs(total_daily_gain):,.2f} ({gain_pct:+.2f}%). "
        "Check the app for detailed scrip-wise analysis."
    )

    # 3. Save to DB
    notification = Notification(
        user_id=user.id,
        title=title,
        message=message,
        type="PORTFOLIO_SUMMARY"
    )
    db.add(notification)
    
    # 4. (SIMULATED) Send Email & Push
    send_simulated_email(user.email, title, message)
    send_simulated_push(user.id, title, message)

def check_and_trigger_alerts():
    """
    Intra-day alert checker. Runs frequently (e.g., every 15 mins)
    Checks: Benchmark drops, Stock drops, Portfolio drops, and Tracklist triggers.
    """
    from ..models.user import AlertSetting, Tracklist
    from ..models.market_data import PriceCache

    db = SessionLocal()
    try:
        # Get Benchmarks
        nifty = db.query(PriceCache).filter(PriceCache.symbol == "NIFTY_50").first()
        sensex = db.query(PriceCache).filter(PriceCache.symbol == "SENSEX").first()
        
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            settings = db.query(AlertSetting).filter(AlertSetting.user_id == user.id).first()
            if not settings: continue

            # 1. Benchmark Alerts
            if nifty and nifty.prev_close and nifty.price:
                nifty_drop = ((nifty.price - nifty.prev_close) / nifty.prev_close * 100)
                if nifty_drop <= -settings.nifty_drop_pct:
                    trigger_alert(db, user, "Market Alert", f"NIFTY 50 has dropped {nifty_drop:.2f}% today!")

            # 2. Portfolio & Stock Alerts
            equities = db.query(Equity).filter(Equity.user_id == user.id, Equity.status == "ACTIVE").all()
            total_mv = 0
            total_gain = 0
            
            for eq in equities:
                curr = eq.current_price or 0
                prev = eq.prev_close or curr
                mv = curr * eq.quantity
                gain = (curr - prev) * eq.quantity
                total_mv += mv
                total_gain += gain
                
                # Individual stock alert
                stock_drop = ((curr - prev) / prev * 100) if prev > 0 else 0
                if stock_drop <= -settings.stock_drop_pct:
                    trigger_alert(db, user, "Stock Alert", f"{eq.symbol} is down {stock_drop:.2f}% today!")

            # Portfolio level alert
            prev_total_mv = total_mv - total_gain
            port_drop = (total_gain / prev_total_mv * 100) if prev_total_mv > 0 else 0
            if port_drop <= -settings.portfolio_drop_pct:
                trigger_alert(db, user, "Portfolio Alert", f"Your portfolio is down {port_drop:.2f}% today!")

            # 3. Tracklist (Radar) Alerts - Use the new RadarEngine
            from ..services.radar_engine import radar_engine
            radar_engine.evaluate_user_radar(db, user)

        db.commit()
    finally:
        db.close()

def trigger_alert(db: Session, user: User, title: str, message: str):
    """Saves alert and prevents spam by checking last 4 hours."""
    from datetime import timedelta
    four_hours_ago = datetime.utcnow() - timedelta(hours=4)
    recent = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.title == title,
        Notification.created_at >= four_hours_ago
    ).first()
    
    if recent: return

    notif = Notification(user_id=user.id, title=title, message=message, type="ALERT")
    db.add(notif)
    send_simulated_push(user.id, title, message)
    send_simulated_email(user.email, title, message)

def send_simulated_email(email, title, message):
    logger.info(f"[EMAIL] To {email} | {title} | {message}")

def send_simulated_push(user_id, title, message):
    logger.info(f"[PUSH] To User {user_id} | {title} | {message}")
