import logging
from sqlalchemy.orm import Session
from ..models import Equity, User
from .market_data import fetch_live_stock_prices, search_ticker_by_name

logger = logging.getLogger(__name__)

def sync_all_equities(db: Session):
    """
    Fetches live prices for ALL active equities in the database and updates their current_price.
    Designed for background scheduler usage.
    """
    logger.info("Starting scheduled equity price sync...")
    
    # 1. Fetch all equities (across all users)
    # Optimization: Filter only ACTIVE status
    # Note: EquityStatus enum handling might be needed if using filter string
    equities = db.query(Equity).all() 
    
    if not equities:
        logger.info("No equities found to sync.")
        return

    # 2. Collect unique symbols to fetch
    prefixed_symbols = []
    symbol_map = {} # lookup -> [equity_objects]
    
    for eq in equities:
        # Skip sold/inactive manually if query didn't filter
        if eq.status and eq.status != "ACTIVE":
            continue
            
        exc_str = eq.exchange.value if hasattr(eq.exchange, 'value') else str(eq.exchange)
        prefix = "BOM" if exc_str == "BSE" else "NSE"
        lookup_key = f"{prefix}:{eq.symbol}"
        
        prefixed_symbols.append(lookup_key)
        
        if lookup_key not in symbol_map:
            symbol_map[lookup_key] = []
        symbol_map[lookup_key].append(eq)
    
    unique_symbols = list(set(prefixed_symbols))
    logger.info(f"Syncing {len(unique_symbols)} unique symbols for {len(equities)} equity records.")
    
    # 3. Bulk Fetch
    live_prices = fetch_live_stock_prices(unique_symbols)
    
    updates_count = 0
    search_attempts = 0
    
    # 4. Update Records
    for lookup_key, eq_list in symbol_map.items():
        price_info = live_prices.get(lookup_key)
        
        if price_info:
            current_price = price_info['price']
            prev_close = price_info.get('prev_close', current_price)
            
            if current_price > 0:
                for eq in eq_list:
                    if eq.current_price != current_price:
                        eq.current_price = current_price
                        eq.prev_close = prev_close
                        updates_count += 1
        else:
            # Fallback Search (limited attempts per run to avoid hanging)
            # Only try searching if price is 0 or missing
            # We pick the first equity in the list to represent the symbol
            representative = eq_list[0]
            if (representative.current_price is None or representative.current_price == 0) and search_attempts < 5:
                # Try finding a better ticker
                search_query = representative.isin or representative.scrip_name
                if search_query:
                    found_ticker = search_ticker_by_name(search_query)
                    if found_ticker:
                        search_attempts += 1
                        logger.info(f"Found better ticker for {representative.symbol}: {found_ticker}")
                        
                        # Fetch price for new ticker
                        search_prices = fetch_live_stock_prices([found_ticker])
                        if found_ticker in search_prices:
                            new_price = search_prices[found_ticker]['price']
                            new_prev = search_prices[found_ticker].get('prev_close', new_price)
                            
                            # Update ALL equities sharing this bad symbol
                            for eq in eq_list:
                                eq.symbol = found_ticker.split('.')[0]
                                eq.exchange = "BSE" if found_ticker.endswith(".BO") else "NSE"
                                eq.current_price = new_price
                                eq.prev_close = new_prev
                                updates_count += 1
                                
    if updates_count > 0:
        db.commit()
        logger.info(f"Successfully updated prices for {updates_count} equity records.")
    else:
        logger.info("No price updates needed.")
