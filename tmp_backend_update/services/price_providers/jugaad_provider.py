from typing import List, Dict
import logging
from jugaad_data.nse import NSELive
from . import PriceProvider
from ...database import SessionLocal
from ...models.market_data import PriceCache

logger = logging.getLogger(__name__)

class JugaadNSEProvider(PriceProvider):
    def __init__(self):
        self.nse = NSELive()

    @property
    def name(self) -> str:
        return "Jugaad Data (NSE Community)"

    def fetch_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        if not symbols:
            return {}

        results = {}
        
        # 1. Get mappings from DB
        db = SessionLocal()
        mapping = {}
        try:
            cache_entries = db.query(PriceCache).filter(PriceCache.symbol.in_(symbols)).all()
            # Mapping from our symbol to NSE symbol (often the same)
            mapping = {c.symbol: (c.yahoo_symbol.replace(".NS", "") if c.yahoo_symbol else c.symbol) for c in cache_entries}
        finally:
            db.close()

        # Try to fetch indices in one go if requested
        indices_data = None
        
        for s in symbols:
            try:
                # Handle Indices
                if s == "^NSEI" or s == "NIFTY 50":
                    if not indices_data:
                        indices_data = self.nse.all_indices()
                    # Jugaad structure check
                    nifty = next((x for x in indices_data['data'] if x['index'] == "NIFTY 50"), None)
                    if nifty:
                        results[s] = {
                            'price': round(float(nifty.get('last', nifty.get('lastPrice', 0))), 2),
                            'prev_close': round(float(nifty.get('previousClose', 0)), 2)
                        }
                    continue

                if s == "^BSESN" or s == "SENSEX":
                    # Jugaad doesn't do BSE well, but often Sensex is in indices data or we skip
                    continue

                # Handle Stocks
                clean_s = mapping.get(s, str(s).strip().upper().replace(".NS", "").replace(".BO", ""))
                
                quote = self.nse.stock_quote(clean_s)
                if quote and 'priceInfo' in quote:
                    info = quote['priceInfo']
                    results[s] = {
                        'price': round(float(info.get('lastPrice', 0)), 2),
                        'prev_close': round(float(info.get('previousClose', 0)), 2)
                    }
                    logger.info(f"Jugaad fetched {s} (NSE: {clean_s}) at {results[s]['price']}")
            except Exception as e:
                logger.error(f"JugaadNSEProvider error for {s}: {e}")
        
        return results

    def fetch_history(self, symbol: str, start_date: str) -> Dict[str, float]:
        raise NotImplementedError("Jugaad provider does not support history yet.")

    def fetch_history_bulk(self, symbols: List[str], start_date: str) -> Dict[str, Dict[str, float]]:
        raise NotImplementedError("Jugaad provider does not support bulk history yet.")
