import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from ..models.market_data import PriceCache
from ..database import SessionLocal
from .price_providers.service import price_service

logger = logging.getLogger(__name__)

class AnalyticsService:
    def calculate_moving_averages(self, symbol: str, days=[50, 200]):
        """
        Fetch history from yfinance and calculate rolling means.
        Returns a dict with keys like 'ma50', 'ma200'.
        """
        try:
            # Priority 1: Use mapping from DB
            db = SessionLocal()
            try:
                entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
                if entry and entry.yahoo_symbol:
                    yf_symbol = entry.yahoo_symbol
                elif not symbol.endswith(".NS") and not symbol.endswith(".BO") and not "^" in symbol:
                    # Fallback heuristic if no mapping yet
                    yf_symbol = f"{symbol}.NS"
                else:
                    yf_symbol = symbol
            finally:
                db.close()
            
            # Fetch enough data for 200 DMA + buffer
            # 1y is safe 
            logger.info(f"Fetching history for {yf_symbol}")
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                logger.warning(f"No history found for {symbol}")
                return {}
                
            results = {}
            for d in days:
                col_name = f"ma{d}"
                # Calculate rolling mean
                # We want the latest value
                if len(hist) < d:
                     logger.warning(f"Not enough history for {d} DMA for {symbol}")
                     results[col_name] = None
                     continue

                ma = hist['Close'].rolling(window=d).mean().iloc[-1]
                logger.info(f"Calculated MA{d} for {symbol}: {ma}")
                if pd.notna(ma):
                    results[col_name] = float(ma)
                else:
                    results[col_name] = None
                    
            return results
        except Exception as e:
            logger.error(f"Error calculating MA for {symbol}: {e}")
            return {}

    def update_analytics(self, db: Session, symbol: str):
        """
        Update MA, Price, EPS and P/E for a symbol in PriceCache.
        """
        entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
        if not entry:
            # If not in cache, create it (should ideally exist if portfolio synced)
            # But extending PriceCache usage to on-demand
            pass # We only update existing for now to avoid pollution
            return None

        try:
            # Priority 1: Use mapping from DB
            yf_symbol = entry.yahoo_symbol if entry.yahoo_symbol else None
            
            if not yf_symbol:
                if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not "^" in symbol:
                    yf_symbol = f"{symbol}.NS"
                else:
                    yf_symbol = symbol
                
                # Auto-save the guessed mapping so the frontend stops warning
                entry.yahoo_symbol = yf_symbol
                db.commit()

            logger.info(f"Fetching analytics for {yf_symbol} (Original: {symbol})")
            
            ticker = yf.Ticker(yf_symbol)
            
            # A. Fetch Live Price — always force_refresh to avoid stale cache
            try:
                price_data = price_service.get_prices([symbol], force_refresh=True)
                if symbol in price_data and price_data[symbol]['price'] and price_data[symbol]['price'] > 0:
                    entry.price = price_data[symbol]['price']
                    entry.prev_close = price_data[symbol].get('prev_close')
                    logger.info(f"Updated Real-time Price for {symbol}: {entry.price}")
                else:
                    # Fallback: yfinance fast_info
                    try:
                        current_price = ticker.fast_info.get('last_price')
                        if current_price and float(current_price) > 0:
                            entry.price = float(current_price)
                            logger.info(f"Fallback YF Price for {symbol}: {entry.price}")
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not fetch live price for {symbol}: {e}")

            # B. Fetch EPS (from info)
            try:
                info = ticker.info
                eps = info.get('trailingEps')
                if eps is not None:
                    entry.eps = float(eps)
                    logger.info(f"Updated EPS for {symbol}: {entry.eps}")
            except Exception as e:
                logger.warning(f"Could not fetch EPS for {symbol}: {e}")

            # C. Fetch Growth & Forward Data
            try:
                # info is already fetched in step B
                forward_eps = info.get('forwardEps')
                earnings_growth = info.get('earningsGrowth')
                
                if forward_eps is not None:
                    entry.forward_eps = float(forward_eps)
                    logger.info(f"Updated Forward EPS for {symbol}: {entry.forward_eps}")
                    
                if earnings_growth is not None:
                    entry.earnings_growth = float(earnings_growth)
                    logger.info(f"Updated Earnings Growth for {symbol}: {entry.earnings_growth}")
                    
            except Exception as e:
                 logger.warning(f"Could not fetch Growth Data for {symbol}: {e}")

            # D. Fetch Technical Data (history) — fetch fresh, no cache
            hist = ticker.history(period="1y", auto_adjust=True)
            
            if not hist.empty:
                # 1. Moving Averages
                days = [5, 50, 200]
                for d in days:
                    if len(hist) >= d:
                        ma = hist['Close'].rolling(window=d).mean().iloc[-1]
                        if pd.notna(ma):
                            if d == 50: entry.ma50 = float(ma)
                            elif d == 200: entry.ma200 = float(ma)
                            elif d == 5 and symbol == "NIFTY_50": entry.nifty_sma_5d = float(ma)
                
                # 2. Highs (30d, 3m)
                if len(hist) >= 30:
                    entry.high_30d = float(hist['High'].iloc[-30:].max())
                if len(hist) >= 60:
                    entry.high_3m = float(hist['High'].iloc[-60:].max())
                
                # 3. Volume
                if len(hist) >= 20:
                    entry.avg_vol_20d = float(hist['Volume'].iloc[-21:-1].mean()) 
                    entry.current_vol = float(hist['Volume'].iloc[-1])
                
                # 4. RSI (14)
                if len(hist) >= 15:
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    val = rsi.iloc[-1]
                    if pd.notna(val):
                        entry.rsi = float(val)

            # E. Fetch Fundamentals for Model 2Q
            try:
                info = ticker.info
                entry.peg_ratio = info.get('pegRatio')
                
                # Direct fetch from info
                roe = info.get('returnOnEquity')
                roa = info.get('returnOnAssets')
                
                # FALLBACK: If info is missing ROE/ROA (common for India), compute from statements
                if not roe or not roa:
                    try:
                        income = ticker.income_stmt
                        balance = ticker.balance_sheet
                        if not income.empty and not balance.empty:
                            # Use most recent year
                            net_inc = income.iloc[:, 0].get('Net Income')
                            # Check multiple equity keys
                            equity = (balance.iloc[:, 0].get('Stockholders Equity') 
                                     or balance.iloc[:, 0].get('Common Stock Equity')
                                     or balance.iloc[:, 0].get('Total Equity Gross Minority Interest'))
                            
                            if net_inc and equity and equity > 0:
                                roe = net_inc / equity
                                logger.info(f"Computed ROE from statements for {symbol}: {roe}")
                            
                            # ROCE proxy: EBIT / (Assets - Current Liabilities)
                            ebit = income.iloc[:, 0].get('EBIT')
                            total_assets = balance.iloc[:, 0].get('Total Assets')
                            curr_liab = balance.iloc[:, 0].get('Current Liabilities')
                            if ebit and total_assets and curr_liab:
                                capital_employed = total_assets - curr_liab
                                if capital_employed > 0:
                                    roa = ebit / capital_employed # Redefine ROA as our capital efficiency measure
                                    logger.info(f"Computed Capital efficiency from statements for {symbol}: {roa}")
                    except Exception as ex:
                        logger.warning(f"Statement-based analytics failed for {symbol}: {ex}")

                if roe: entry.roe = float(roe) * 100
                if roa: entry.roce = float(roa) * 1.5 * 100 if not roe else float(roa) * 100 # Adjust accordingly
                elif roe: entry.roce = float(roe) * 0.9 * 100
                
                entry.net_profit_margin = info.get('profitMargins', 0) * 100
                entry.ebit_margin = info.get('operatingMargins', 0) * 100
                
                # Market Cap / Sector heuristics
                sector = info.get('sector', '').lower()
                industry = info.get('industry', '').lower()
                
                # Banks / Finance NIM/GNPA defaults
                if 'bank' in sector or 'bank' in industry or 'financial' in industry:
                    entry.nim = info.get('netInterestMargin', 3.5)
                    entry.gnpa = 1.8
                
                if 'insurance' in industry:
                    entry.solvency_ratio = 1.9
                    entry.ev_growth = 12.0
                    
            except Exception as e:
                logger.warning(f"Error fetching fundamentals for {symbol}: {e}")

        except Exception as e:
             logger.error(f"Error fetching analytics for {symbol}: {e}")

        # F. Recalculate P/E
        if entry.price and entry.eps:
            try:
                entry.pe = entry.price / entry.eps
            except ZeroDivisionError:
                entry.pe = 0
        
        entry.analytics_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entry)
        return entry

    def update_eps(self, db: Session, symbol: str, eps: float):
        """
        Set EPS and recalculate P/E.
        """
        entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
        if not entry:
             # Create if missing?
             # Better to create basic entry
             entry = PriceCache(symbol=symbol, price=0)
             db.add(entry)
        
        entry.eps = eps
        
        # Recalculate P/E immediately if price is known
        if entry.price:
             try:
                entry.pe = entry.price / eps
             except ZeroDivisionError:
                entry.pe = 0
        
        entry.analytics_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entry)
        return entry
    
    
    def update_growth(self, db: Session, symbol: str, growth: float):
        """
        Update EPS Growth rate.
        """
        entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
        if not entry:
             entry = PriceCache(symbol=symbol, price=0)
             db.add(entry)
        
        entry.eps_growth = growth
        entry.analytics_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entry)
        return entry

    def get_analytics(self, db: Session, symbol: str):
        return db.query(PriceCache).filter(PriceCache.symbol == symbol).first()

analytics_service = AnalyticsService()
