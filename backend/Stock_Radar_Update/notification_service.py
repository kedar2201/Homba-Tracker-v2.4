import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user import User, Notification
from ..models.equity import Equity
from ..services.calculations import get_equity_current_value

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

    # 2. Prepare Notification Message
    gain_arrow = "▲" if total_daily_gain >= 0 else "▼"
    prev_value = total_market_value - total_daily_gain
    gain_pct = (total_daily_gain / prev_value * 100) if prev_value > 0 else 0
    
    title = f"Market Close Report {datetime.now().strftime('%d %b')}"
    message = (
        f"Hi {user.username}, your portfolio closed at ₹{total_market_value:,.2f}. "
        f"Daily Movement: {gain_arrow} ₹{abs(total_daily_gain):,.2f} ({gain_pct:+.2f}%). "
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
    
    # 4. (SIMULATED) Send Email
    send_simulated_email(user.email, title, message)
    
    # 5. (SIMULATED) Send Push Notification
    send_simulated_push(user.id, title, message)

def check_and_trigger_alerts():
    """
    Intra-day alert checker. Runs frequently to check for drops based on user settings.
    """
    from ..models.user import AlertSetting
    from ..models.market_data import PriceCache

    db = SessionLocal()
    try:
        # Get Nifty & Sensex movement
        nifty = db.query(PriceCache).filter(PriceCache.symbol == "NIFTY_50").first()
        sensex = db.query(PriceCache).filter(PriceCache.symbol == "SENSEX").first()
        
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            settings = db.query(AlertSetting).filter(AlertSetting.user_id == user.id).first()
            if not settings: continue

            # 1. Check Benchmark Drop
            if nifty and nifty.change_pct and nifty.change_pct <= -settings.nifty_drop_pct:
                trigger_alert(db, user, "Market Alert", f"Benchmark NIFTY 50 is down {nifty.change_pct:.2f}%!")
            
            # 2. Check individual stock & Portfolio drops
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
                    trigger_alert(db, user, "Stock Alert", f"{eq.symbol} has dropped {stock_drop:.2f}% today!")

            # 3. Portfolio drop alert
            prev_total_mv = total_mv - total_gain
            port_drop = (total_gain / prev_total_mv * 100) if prev_total_mv > 0 else 0
            if port_drop <= -settings.portfolio_drop_pct:
                trigger_alert(db, user, "Portfolio Alert", f"Your total portfolio is down {port_drop:.2f}% today!")

            # 4. Check Tracklist triggers
            from ..models.user import Tracklist
            from ..models.rating import Rating
            track_items = db.query(Tracklist).filter(Tracklist.user_id == user.id).all()
            for item in track_items:
                live = db.query(PriceCache).filter(PriceCache.symbol == item.symbol).first()
                if not live: continue

                # Condition 1: Target Price
                if item.target_price and live.price <= item.target_price:
                    trigger_alert(db, user, "Buy Opportunity", f"{item.symbol} reached target price ₹{item.target_price}!")

                # Condition 2: Technicals (DMA)
                rating = db.query(Rating).filter(Rating.symbol == item.symbol).first()
                if rating:
                    # Current price vs DMA
                    if item.trigger_dma50 and rating.dma_50 and live.price >= rating.dma_50:
                        # Price crossed above 50 DMA
                        trigger_alert(db, user, "Technicals Alert", f"{item.symbol} is now above 50 DMA (₹{rating.dma_50:.2f})!")
                    
                    if item.trigger_dma200 and rating.dma_200 and live.price >= rating.dma_200:
                        trigger_alert(db, user, "Technicals Alert", f"{item.symbol} is now above 200 DMA (₹{rating.dma_200:.2f})!")

        db.commit()
    finally:
        db.close()

def trigger_alert(db: Session, user: User, title: str, message: str):
    """Save alert to notifications and simulate delivery."""
    from datetime import timedelta
    # Check if we already sent this exact title to this user in the last 4 hours
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
    logger.info(f"[EMAIL SIMULATION] Sending to {email} | Subject: {title} | Body: {message}")

def send_simulated_push(user_id, title, message):
    logger.info(f"[PUSH SIMULATION] Sending to User {user_id} | Title: {title} | Body: {message}")
