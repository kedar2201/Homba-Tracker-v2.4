import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.user import User, Tracklist, RadarSignalLog, Notification
from ..models.market_data import PriceCache

logger = logging.getLogger(__name__)

class RadarEngine:
    def evaluate_all(self, db: Session):
        """Main entry point to evaluate all users' tracklists."""
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            self.evaluate_user_radar(db, user)

    def evaluate_user_radar(self, db: Session, user: User):
        # Fetch User's scoring config
        from ..models.user import RadarScoringWeights
        config = db.query(RadarScoringWeights).filter(RadarScoringWeights.user_id == user.id).first()
        if not config:
            config = RadarScoringWeights(user_id=user.id)

        track_items = db.query(Tracklist).filter(Tracklist.user_id == user.id).all()
        for item in track_items:
            live = db.query(PriceCache).filter(PriceCache.symbol == item.symbol).first()
            if not live or not live.price: continue
            
            # Calculate Score
            score, details, signals_met, breakdown = self.calculate_score(item, live, db, config)
            
            # Update Score and Breakdown in Tracklist entry
            item.last_alert_score = score # We use this as the cached score
            # If we had a JSON column for breakdown, we'd save it here. 
            # For now, we update it and commit later.
            
            # Save to Log if score is significant (e.g. > 40)
            if score >= 40:
                self._log_signal(db, user.id, item.symbol, score, details)
            
            # Check Alert Trigger
            self._handle_alert(db, user, item, score, details, signals_met)
        
        db.commit()

    def calculate_score(self, item: Tracklist, live: PriceCache, db: Session, config=None):
        """
        Model 2Q Scoring Engine:
        Tech (50), Val (20), Quality (20), Risk (-10)
        """
        # Resolve Weights (Model-2Q structure)
        w_dip = item.weight_dip if item.weight_dip > 0 else (config.weight_dip if config else 12)
        w_rsi = item.weight_rsi if item.weight_rsi > 0 else (config.weight_rsi if config else 8)
        w_dma = item.weight_dma if item.weight_dma > 0 else (config.weight_dma if config else 12)
        w_breakout = item.weight_breakout if item.weight_breakout > 0 else (config.weight_breakout if config else 12)
        w_market = item.weight_market_bonus if item.weight_market_bonus > 0 else (config.weight_market_bonus if config else 6)
        
        w_pe_disc = item.weight_pe_discount if item.weight_pe_discount > 0 else (config.weight_pe_discount if config else 12)
        w_peg = item.weight_peg if item.weight_peg > 0 else (config.weight_peg if config else 8)

        w_roe = item.weight_roe if item.weight_roe > 0 else (config.weight_roe if config else 10)
        w_q2 = item.weight_roce_nim_ev if item.weight_roce_nim_ev > 0 else (config.weight_roce_nim_ev if config else 10)
        w_q3 = item.weight_quality_3 if item.weight_quality_3 > 0 else (config.weight_quality_3 if config else 0)

        w_risk_pe = item.weight_risk_pe if item.weight_risk_pe > 0 else (config.weight_risk_pe if config else 2)
        w_risk_earn = item.weight_risk_earnings if item.weight_risk_earnings > 0 else (config.weight_risk_earnings if config else 4)
        w_risk_debt = item.weight_risk_debt if item.weight_risk_debt > 0 else (config.weight_risk_debt if config else 4)

        # Resolve Toggles 
        # Logic: If item.weight_dip > 0, we assume 'has_custom' is true for scrip-level override
        has_custom = item.use_custom_weights or (item.weight_dip > 0)
        u_dip = item.use_dip if has_custom else (config.use_dip if config else True)
        u_rsi = item.use_rsi if has_custom else (config.use_rsi if config else True)
        u_dma = item.use_dma if has_custom else (config.use_dma if config else True)
        u_breakout = item.use_breakout if has_custom else (config.use_breakout if config else True)
        u_market = item.use_market_bonus if has_custom else (config.use_market_bonus if config else True)
        u_pe_disc = item.use_pe_discount if has_custom else (config.use_pe_discount if config else True)
        u_peg = item.use_peg if has_custom else (config.use_peg if config else True)
        u_quality = item.use_quality if has_custom else (config.use_quality if config else True)
        u_risk = item.use_risk if has_custom else (config.use_risk if config else True)

        tech_score = 0
        val_score = 0
        qual_score = 0
        risk_deduction = 0
        details = []
        signals_met = {"dip": False, "rsi": False, "dma": False, "breakout": False}

        # --- 1. TECHNICAL STRENGTH (50) ---
        # ** FIX: "Either/Or" Logic **
        # Instead of penalizing a stock for a Bounce when it's Breaking Out, we calculate both
        # logic pathways separately and use whichever logic scores higher.

        # Pathway A: Mean Reversion (Dip + RSI + DMA)
        reversion_score = 0
        rev_details = []
        if u_dip and live.high_30d and live.high_30d > 0:
            dip_pct = ((live.high_30d - live.price) / live.high_30d) * 100
            # Softened: Award points earlier to ensure we catch good dips
            if dip_pct >= item.dip_percent:
                reversion_score += w_dip
                rev_details.append(f"Dip: {dip_pct:.1f}%")
                signals_met["dip"] = True
            elif dip_pct >= (item.dip_percent * 0.75):
                reversion_score += round(w_dip * 0.66)
                rev_details.append(f"Dip: near")

        if u_rsi and live.rsi:
            if live.rsi <= item.rsi_threshold:
                reversion_score += w_rsi
                rev_details.append(f"RSI: {live.rsi:.1f}")
                signals_met["rsi"] = True
            elif live.rsi <= (item.rsi_threshold + 5): # Softened
                reversion_score += round(w_rsi * 0.6)
                rev_details.append(f"RSI: near")

        if u_dma:
            dma_met = False
            w_half = round(w_dma / 2)
            if live.ma50:
                dist_50 = abs(live.price - live.ma50) / live.ma50 * 100
                # Softened: Proximity to 5% instead of tight 2%
                if dist_50 <= (item.near_50dma_percent + 3):
                    reversion_score += w_half
                    dma_met = True
            if live.ma200:
                dist_200 = abs(live.price - live.ma200) / live.ma200 * 100
                # Softened: Proximity to 5% instead of tight 2%
                if dist_200 <= (item.near_200dma_percent + 2):
                    reversion_score += (w_dma - w_half)
                    dma_met = True
            if dma_met:
                rev_details.append("DMA Prox")
                signals_met["dma"] = True

        # Pathway B: Momentum (Breakout)
        momentum_score = 0
        mom_details = []
        is_breakout = False
        vol_spike = False
        if u_breakout and item.breakout_enabled and (live.high_3m is not None) and (live.avg_vol_20d is not None):
            is_breakout = live.price >= (live.high_3m * 0.98) # Softened: within 2% of highs
            vol_spike = live.current_vol >= (live.avg_vol_20d * 1.5) if live.avg_vol_20d > 0 else False
            
            if is_breakout and vol_spike:
                momentum_score += (w_breakout + w_dip + w_rsi) # Grant the full reversion points as momentum
                mom_details.append("Breakout+Vol")
                signals_met["breakout"] = True
            elif is_breakout:
                momentum_score += round((w_breakout + w_dip + w_rsi) * 0.8)
                mom_details.append("Breakout Proximity")
            elif vol_spike:
                momentum_score += round(w_breakout * 0.4)
                mom_details.append("Vol Spike")
                
            # If relying strictly on momentum, we still assess DMA for trend confirmation
            if dma_met and is_breakout:
                momentum_score += w_dma

        # Choose the stronger technical setup
        logic_path = "Reversion"
        if momentum_score > reversion_score:
            tech_score += momentum_score
            details.extend(mom_details)
            logic_path = "Momentum"
        else:
            tech_score += reversion_score
            details.extend(rev_details)

        if u_market:
            m_bonus = self._get_market_bonus_points(db)
            actual_bonus = round(m_bonus * (w_market / 5.0))
            if actual_bonus > 0:
                tech_score += actual_bonus
                details.append(f"Mkt Bonus +{actual_bonus}")

        # --- 2. VALUATION (20) ---
        if u_pe_disc and live.pe and live.pe_avg_5y and live.pe_avg_5y > 0:
            disc = (live.pe_avg_5y - live.pe) / live.pe_avg_5y * 100
            # Softened: 15% discount gets full points instead of 20%
            if disc >= 15: val_score += w_pe_disc
            elif disc >= 8: val_score += round(w_pe_disc * 0.8)
            elif disc >= 3: val_score += round(w_pe_disc * 0.4)

        if u_peg and live.peg_ratio is not None:
            # Softened: Pegs up to 1.3 get full value
            if live.peg_ratio <= 1.3: val_score += w_peg
            elif live.peg_ratio <= 1.8: val_score += round(w_peg * 0.6)

        # --- 3. QUALITY (20) - SECTOR AWARE ---
        if u_quality:
            # Resolve live fundamentals (Prefer PriceCache if item's manual entry is 0/empty)
            r_roe  = max(item.roe,  live.roe or 0)
            r_roce = max(item.roce, live.roce or 0)
            r_nim  = max(item.nim,  live.nim or 0)
            r_gnpa = item.gnpa if item.gnpa > 0 else (live.gnpa or 1.8) # Default GNPA 1.8 for banks if unknown
            r_ev   = max(item.ev_growth, live.ev_growth or 0)
            r_solv = max(item.solvency_ratio, live.solvency_ratio or 0)

            # ROE (Max 10) - Softened from 25% down to 18% realistically
            if r_roe >= 18: qual_score += w_roe
            elif r_roe >= 15: qual_score += round(w_roe * 0.8)
            elif r_roe >= 10: qual_score += round(w_roe * 0.6)
            elif r_roe >= 5: qual_score += round(w_roe * 0.3)
            
            if item.sector_type in ['bank', 'nbfc']:
                # NIM (Max 5)
                w_nim = round(w_q2 * 0.5)
                if r_nim >= 3.5: qual_score += w_nim
                elif r_nim >= 2.5: qual_score += round(w_nim * 0.6)
                # Asset Quality GNPA (Max 5)
                w_gnpa = w_q2 - w_nim
                if r_gnpa < 2.5: qual_score += w_gnpa
                elif r_gnpa <= 4.5: qual_score += round(w_gnpa * 0.6)
            elif item.sector_type == 'insurance':
                # EV Growth (Max 5)
                w_ev = round(w_q2 * 0.5)
                if r_ev >= 12: qual_score += w_ev
                elif r_ev >= 8: qual_score += round(w_ev * 0.6)
                # Solvency (Max 5)
                w_solv = w_q2 - w_ev
                if r_solv >= 1.8: qual_score += w_solv
                elif r_solv >= 1.5: qual_score += round(w_solv * 0.6)
            else:
                # Standard ROCE (Max 10) - Softened
                if r_roce >= 18: qual_score += w_q2
                elif r_roce >= 15: qual_score += round(w_q2 * 0.8)
                elif r_roce >= 10: qual_score += round(w_q2 * 0.6)
                elif r_roce >= 5: qual_score += round(w_q2 * 0.3)

        # --- 4. RISK (-10) ---
        if u_risk:
            # PE Risk (-2)
            if live.pe and live.pe > 80: risk_deduction += w_risk_pe
            elif live.pe and live.pe > 60: risk_deduction += round(w_risk_pe * 0.5)
            # Earnings Risk (-4)
            eps_yoy_growth = getattr(live, "eps_yoy_growth", None)
            if eps_yoy_growth is not None and eps_yoy_growth < 0:
                risk_deduction += w_risk_earn
            # Debt Risk (-4)
            debt_yoy_growth = getattr(live, "debt_yoy_growth", None)
            if debt_yoy_growth is not None and debt_yoy_growth > 25:
                risk_deduction += w_risk_debt

        # --- NORMALIZATION ---
        max_pos = 0
        if u_dip: max_pos += w_dip
        if u_rsi: max_pos += w_rsi
        if u_dma: max_pos += w_dma
        if u_breakout: max_pos += w_breakout
        if u_market: max_pos += w_market
        if u_pe_disc: max_pos += w_pe_disc
        if u_peg: max_pos += w_peg
        if u_quality: max_pos += (w_roe + w_q2 + w_q3)
        
        if max_pos == 0: max_pos = 100

        final_raw = tech_score + val_score + qual_score - risk_deduction
        normalized = round((max(0, final_raw) / max_pos) * 100)
        
        breakdown = {
            "tech": tech_score,
            "val": val_score,
            "qual": qual_score,
            "risk": risk_deduction,
            "max": max_pos,
            "logic": logic_path
        }
        
        return min(normalized, 100), details, signals_met, breakdown

    def _get_market_bonus_points(self, db: Session):
        """
        Bonus points based on Nifty 5-day correction:
        - Down 3% in 5 days: +5 pts
        - Down 2% in 5 days: +3 pts
        """
        nifty = db.query(PriceCache).filter(PriceCache.symbol == "NIFTY_50").first()
        if not nifty or not nifty.price or not nifty.prev_close: return 0
        
        # Simplified 5-day check using price vs stored nifty_sma_5d as proxy
        # Real implementation would calculate from history.
        if not nifty.nifty_sma_5d: return 0
        
        correction = (nifty.nifty_sma_5d - nifty.price) / nifty.nifty_sma_5d * 100
        if correction >= 3.0: return 5
        if correction >= 2.0: return 3
        return 0

    def _log_signal(self, db: Session, user_id: int, symbol: str, score: int, details: list):
        log = RadarSignalLog(
            user_id=user_id,
            symbol=symbol,
            confidence_score=score,
            signal_summary=", ".join(details)
        )
        db.add(log)

    def _handle_alert(self, db: Session, user: User, item: Tracklist, score: int, details: list, signals_met: dict):
        """Trigger notification based on integrated signals OR score threshold."""
        
        # Check Integrated Signal Trigger: All selected enabled signals must be met
        enabled_signals_met = True
        checks_performed = 0
        
        if item.trigger_dip:
            checks_performed += 1
            if not signals_met["dip"]: enabled_signals_met = False
        if item.trigger_rsi:
            checks_performed += 1
            if not signals_met["rsi"]: enabled_signals_met = False
        if item.trigger_dma:
            checks_performed += 1
            if not signals_met["dma"]: enabled_signals_met = False
        if item.trigger_breakout:
            checks_performed += 1
            if not signals_met["breakout"]: enabled_signals_met = False
            
        strict_signal_triggered = (checks_performed > 0) and enabled_signals_met
        score_triggered = item.trigger_score and (score >= item.min_confidence_score)
        
        if not (strict_signal_triggered or score_triggered):
            return

        # Cooldown Logic: Once alerted, no repeat alert for 1 day unless score improves by 10+
        today = datetime.utcnow().date()
        last_triggered = item.last_triggered_at.date() if item.last_triggered_at else None
        
        should_alert = False
        if last_triggered != today:
            should_alert = True
        elif score >= item.last_alert_score + 10:
            should_alert = True
            
        if should_alert:
            trigger_reason = "Integrated Signals Met" if strict_signal_triggered else f"Confidence Score: {score}"
            title = f"\ud83d\udd0e {item.symbol} Radar Alert ({trigger_reason})"
            message = " + ".join(details)
            
            notif = Notification(
                user_id=user.id,
                title=title,
                message=message,
                type="ALERT"
            )
            db.add(notif)
            
            # Update item tracking
            item.last_triggered_at = datetime.utcnow()
            item.last_alert_score = score
            db.commit()

radar_engine = RadarEngine()
