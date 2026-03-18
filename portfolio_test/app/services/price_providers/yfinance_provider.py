import yfinance as yf
import pandas as pd
import logging
from typing import List, Dict, Any
from datetime import datetime
from . import PriceProvider
from ...database import SessionLocal
from ...models.market_data import PriceCache

logger = logging.getLogger(__name__)

class YFinanceProvider(PriceProvider):
    @property
    def name(self) -> str:
        return "Yahoo Finance (Delayed)"

    def fetch_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        if not symbols:
            return {}

        results = {}
        yf_symbols = []
        symbol_map = {}
        
        # 1. Map internal symbols to Yahoo symbols using DB
        db = SessionLocal()
        try:
            cache_entries = db.query(PriceCache).filter(PriceCache.symbol.in_(symbols)).all()
            mapping = {c.symbol: c.yahoo_symbol for c in cache_entries if c.yahoo_symbol}
        finally:
            db.close()

        for s in symbols:
            yf_ticker = mapping.get(s)
            
            if not yf_ticker:
                # Fallback for indices if not in cache yet (though population script should have covered it)
                if s.startswith("^"):
                    yf_ticker = s
                else:
                    logger.warning(f"No Yahoo Symbol mapping found for {s}, skipping fetch.")
                    continue
                
            yf_symbols.append(yf_ticker)
            symbol_map[yf_ticker] = s
                
            yf_symbols.append(yf_ticker)
            symbol_map[yf_ticker] = s

        # Separate indices for single fetch (more reliable)
        indices_to_fetch = []
        bulk_yf_symbols = []
        
        for yf_ticker, orig in symbol_map.items():
            if yf_ticker.startswith("^"):
                indices_to_fetch.append(yf_ticker)
            else:
                bulk_yf_symbols.append(yf_ticker)
                
        # Fetch indices individually
        for yf_ticker in indices_to_fetch:
            self._fetch_single(yf_ticker, symbol_map[yf_ticker], results)

        # Process bulk symbols in chunks
        chunk_size = 50
        for i in range(0, len(bulk_yf_symbols), chunk_size):
            chunk = bulk_yf_symbols[i:i + chunk_size]
            try:
                # Use 20d to be sure of historical points
                data = yf.download(chunk, period="20d", interval="1d", progress=False, auto_adjust=True)
                
                if data.empty:
                    # Fallback to individual Ticker fetches if bulk fails
                    logger.warning(f"Bulk YFinance fetch failed for chunk, trying individually...")
                    for yf_ticker in chunk:
                        self._fetch_single(yf_ticker, symbol_map[yf_ticker], results)
                    continue
                    
                has_multi_index = isinstance(data.columns, pd.MultiIndex)
                
                for yf_ticker in chunk:
                    orig_symbol = symbol_map[yf_ticker]
                    try:
                        if has_multi_index:
                            if yf_ticker not in data['Close'].columns:
                                self._fetch_single(yf_ticker, orig_symbol, results)
                                continue
                            ticker_series = data['Close'][yf_ticker].dropna()
                        else:
                            ticker_series = data['Close'].dropna()
                        
                        if not ticker_series.empty:
                            current_price = float(ticker_series.iloc[-1])
                            prev_close = float(ticker_series.iloc[-2]) if len(ticker_series) >= 2 else current_price
                                
                            results[orig_symbol] = {
                                'price': round(current_price, 2),
                                'prev_close': round(prev_close, 2)
                            }
                        else:
                            self._fetch_single(yf_ticker, orig_symbol, results)
                    except Exception as e:
                        logger.error(f"Error processing {yf_ticker} in YFinanceProvider: {e}")
            except Exception as e:
                logger.error(f"Error in YFinanceProvider chunk: {e}")

        return results

    def fetch_history(self, symbol: str, start_date: str) -> Dict[str, float]:
        """
        Fetch historical prices for a given symbol.
        """
        # Map internal symbol to Yahoo symbol using DB
        db = SessionLocal()
        try:
            cache_entry = db.query(PriceCache).filter(PriceCache.symbol == symbol).first()
            yf_ticker = cache_entry.yahoo_symbol if cache_entry and cache_entry.yahoo_symbol else None
            
            if not yf_ticker and symbol.startswith("^"):
                yf_ticker = symbol
        finally:
            db.close()

        if not yf_ticker:
            logger.warning(f"No Yahoo Symbol mapping found for {symbol}, cannot fetch history.")
            return {}



        try:
            # Try Ticker.history first for indices as it proved more reliable in tests
            if yf_ticker.startswith("^"):
                try:
                    t = yf.Ticker(yf_ticker)
                    hist = t.history(start=start_date)
                    if not hist.empty:
                        prices = {}
                        for dt, row in hist.iterrows():
                            date_str = dt.strftime("%Y-%m-%d")
                            prices[date_str] = round(float(row['Close']), 2)
                        return prices
                except:
                    pass

            logger.info(f"Fetching history for {yf_ticker} since {start_date}")
            data = yf.download(yf_ticker, start=start_date, interval="1d", progress=False, auto_adjust=True)
            
            if data.empty:
                # One last try with Ticker if download failed and we haven't tried it yet
                if not yf_ticker.startswith("^"):
                     t = yf.Ticker(yf_ticker)
                     hist = t.history(start=start_date)
                     if not hist.empty:
                        prices = {}
                        for dt, row in hist.iterrows():
                            date_str = dt.strftime("%Y-%m-%d")
                            prices[date_str] = round(float(row['Close']), 2)
                        return prices
                return {}
            
            # Close prices indexed by date
            prices = {}
            for dt, row in data.iterrows():
                date_str = dt.strftime("%Y-%m-%d")
                prices[date_str] = round(float(row['Close']), 2)
            return prices
        except Exception as e:
            logger.error(f"Error fetching history for {yf_ticker} in YFinanceProvider: {e}")
            return {}

    def fetch_history_bulk(self, symbols: List[str], start_date: str) -> Dict[str, Dict[str, float]]:
        """
        Fetch historical prices for multiple symbols in one go.
        """
        if not symbols:
            return {}

        results = {s: {} for s in symbols}
        
        # Separate indices for single fetch
        indices_to_fetch = []
        bulk_symbols = []
        
        for s in symbols:
            if str(s).strip().upper().startswith("^") or s in ["^NSEI", "^BSESN"]:
                indices_to_fetch.append(s)
            else:
                bulk_symbols.append(s)
                
        # Fetch indices individually
        for s in indices_to_fetch:
            results[s] = self.fetch_history(s, start_date)

        if not bulk_symbols:
            return results

        # Map internal symbols to Yahoo symbols using DB
        db = SessionLocal()
        try:
            cache_entries = db.query(PriceCache).filter(PriceCache.symbol.in_(bulk_symbols)).all()
            yf_to_orig = {c.yahoo_symbol: c.symbol for c in cache_entries if c.yahoo_symbol}
            yf_tickers = list(yf_to_orig.keys())
        finally:
            db.close()
            
        # Add indices if any
        for s in bulk_symbols:
            if s.startswith("^") and s not in yf_to_orig.values():
                 yf_tickers.append(s)
                 yf_to_orig[s] = s

        try:
            logger.info(f"Bulk fetching history for {len(yf_tickers)} symbols since {start_date}")
            data = yf.download(yf_tickers, start=start_date, interval="1d", progress=False, auto_adjust=True, threads=True)
            if data.empty:
                return results
            
            has_multi_index = isinstance(data.columns, pd.MultiIndex)
            
            for yf_ticker in yf_tickers:
                orig = yf_to_orig[yf_ticker]
                try:
                    if has_multi_index:
                        series = data['Close'][yf_ticker].dropna() if yf_ticker in data['Close'].columns else pd.Series()
                    else:
                        series = data['Close'].dropna() if 'Close' in data.columns else pd.Series()
                    
                    for dt, val in series.items():
                        results[orig][dt.strftime("%Y-%m-%d")] = round(float(val), 2)
                except Exception as e:
                    logger.error(f"Error processing {yf_ticker} in history bulk: {e}")
            
            return results
        except Exception as e:
            logger.error(f"Error in YFinanceProvider history bulk: {e}")
            return results

    def _fetch_single(self, yf_ticker: str, orig_symbol: str, results: Dict):
        """Individual fetch fallback for stubborn tickers"""
        try:
            t = yf.Ticker(yf_ticker)
            # Try history first - most reliable
            hist = t.history(period="2d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else current_price
                results[orig_symbol] = {
                    'price': round(current_price, 2),
                    'prev_close': round(prev_close, 2)
                }
                logger.info(f"Individual History fetch Succeeded for {yf_ticker}")
                return

            # Fallback to fast_info
            if hasattr(t, 'fast_info'):
                info = t.fast_info
                price = info.get('last_price') or info.get('lastPrice')
                if price is not None:
                    results[orig_symbol] = {
                        'price': round(float(price), 2),
                        'prev_close': round(float(info.get('previous_close', info.get('previousClose', price))), 2)
                    }
                    logger.info(f"Individual FastInfo fetch Succeeded for {yf_ticker}")
            else:
                logger.warning(f"Ticker has no fast_info attribute for {yf_ticker}")
        except Exception as e:
            logger.error(f"Individual fetch Failed for {yf_ticker}: {e}")
