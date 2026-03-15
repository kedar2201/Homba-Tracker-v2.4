import logging
import time
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from . import PriceProvider
from .yfinance_provider import YFinanceProvider
from .broker_provider import BrokerProvider
from .jugaad_provider import JugaadNSEProvider
from ...models.market_data import PriceCache
from ...database import SessionLocal

logger = logging.getLogger(__name__)

class PriceService:
    def __init__(self, primary_provider: PriceProvider, fallback_provider: Optional[PriceProvider] = None, cache_expiry_minutes: int = 15):
        self.provider = primary_provider
        self.fallback_provider = fallback_provider
        self.cache_expiry_minutes = cache_expiry_minutes

    def get_prices(self, symbols: List[str], force_refresh: bool = False) -> Dict[str, Dict[str, float]]:
        if not symbols:
            return {}

        db = SessionLocal()
        try:
            results = {}
            symbols_to_fetch = []
            
            # 1. Prepare Cache Lookup
            expiry_time = datetime.utcnow() - timedelta(minutes=self.cache_expiry_minutes)
            cached_entries = db.query(PriceCache).filter(PriceCache.symbol.in_(symbols)).all()
            cache_map = {c.symbol: c for c in cached_entries}

            for s in symbols:
                # 2. Check DB Cache (Skip check if force_refresh is True)
                entry = cache_map.get(s)
                if not force_refresh and entry and entry.updated_at > expiry_time and entry.price is not None:
                    results[s] = {
                        'price': entry.price,
                        'prev_close': entry.prev_close
                    }
                else:
                    symbols_to_fetch.append(s)

            # 2. Fetch missing from primary provider
            if symbols_to_fetch:
                logger.info(f"Fetching {len(symbols_to_fetch)} symbols from {self.provider.name}")
                new_prices = self.provider.fetch_prices(symbols_to_fetch)
                
                # 3. Fallback for remaining symbols
                remaining = [s for s in symbols_to_fetch if s not in new_prices]
                if remaining and self.fallback_provider:
                    logger.info(f"Fallback to {self.fallback_provider.name} for {len(remaining)} symbols: {remaining}")
                    fallback_prices = self.fallback_provider.fetch_prices(remaining)
                    new_prices.update(fallback_prices)

                # 4. Final Fallback: Use stale cache for anything still missing
                final_missing = [s for s in symbols_to_fetch if s not in new_prices]
                for s in final_missing:
                    entry = cache_map.get(s)
                    if entry and entry.price is not None:
                        new_prices[s] = {
                            'price': entry.price,
                            'prev_close': entry.prev_close
                        }
                        logger.info(f"Using stale cache for {s}")
                    else:
                        new_prices[s] = {
                            'price': 0.0,
                            'prev_close': 0.0
                        }
                        logger.info(f"Caching 0.0 for unresolved symbol {s} to prevent blocking")


                # 5. Update DB Cache
                for s, info in new_prices.items():
                    results[s] = info
                    self._update_db_cache(db, s, info)
                
                db.commit()

            return results
        finally:
            db.close()

    def get_history(self, symbol: str, start_date: str) -> Dict[str, float]:
        """
        Fetch historical prices for a given symbol.
        No caching for now to keep it simple.
        """
        try:
            return self.provider.fetch_history(symbol, start_date)
        except Exception as e:
            logger.error(f"Error in PriceService.get_history for {symbol}: {e}")
            if self.fallback_provider:
                try:
                    return self.fallback_provider.fetch_history(symbol, start_date)
                except:
                    pass
            return {}

    def get_history_bulk(self, symbols: List[str], start_date: str) -> Dict[str, Dict[str, float]]:
        """
        Fetch historical prices for multiple symbols at once.
        """
        try:
            return self.provider.fetch_history_bulk(symbols, start_date)
        except Exception as e:
            logger.error(f"Error in PriceService.get_history_bulk: {e}")
            if self.fallback_provider:
                try:
                    return self.fallback_provider.fetch_history_bulk(symbols, start_date)
                except:
                    pass
            return {s: {} for s in symbols}

    def _update_db_cache(self, db: Session, symbol: str, info: Dict[str, float]):
        try:
            entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
            if entry:
                entry.price = info['price']
                entry.prev_close = info.get('prev_close')
                entry.updated_at = datetime.utcnow()
            else:
                entry = PriceCache(
                    symbol=symbol,
                    price=info['price'],
                    prev_close=info.get('prev_close')
                )
                db.add(entry)
        except Exception as e:
            logger.error(f"Error updating DB cache for {symbol}: {e}")

# Global Price Service Instance
# Primary: YFinance (Global - more reliable on Cloud IP)
# Fallback: Jugaad 
price_service = PriceService(YFinanceProvider(), JugaadNSEProvider())

def get_price_service():
    return price_service

def switch_provider(provider_name: str):
    global price_service
    if provider_name.lower() == "broker":
        price_service = PriceService(BrokerProvider(), YFinanceProvider())
    elif provider_name.lower() == "jugaad":
        price_service = PriceService(JugaadNSEProvider(), YFinanceProvider())
    else:
        # Default for cloud: YFinance primary
        price_service = PriceService(YFinanceProvider(), JugaadNSEProvider())
    logger.info(f"Price provider switched to: {price_service.provider.name}")
