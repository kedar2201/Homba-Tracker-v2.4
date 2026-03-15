from fastapi import APIRouter
import requests
from typing import List, Dict, Any

router = APIRouter(
    tags=["Market Data"],
)

@router.get("/indices")
def get_market_indices():
    """Fetch Nifty 50 and Sensex current values with high reliability"""
    from ..services.price_providers.service import price_service
    symbols = {'^NSEI': 'NIFTY 50', '^BSESN': 'SENSEX'}
    # Force refresh to ensure we bypass cache and get the latest live minute candle
    results = price_service.get_prices(list(symbols.keys()), force_refresh=True)
    
    indices = []
    for symbol, display_name in symbols.items():
        data = results.get(symbol)
        if data:
            price = data['price']
            prev = data.get('prev_close', price)
            change = price - prev
            indices.append({
                'name': display_name,
                'value': round(price, 2),
                'change': round(change, 2),
                'changePercent': round((change / prev) * 100, 2) if prev else 0
            })
            
    return indices

@router.get("/provider")
def get_provider_status():
    from ..services.price_providers.service import get_price_service
    service = get_price_service()
    return {
        "active_provider": service.provider.name,
        "cache_expiry_minutes": service.cache_expiry_minutes
    }

@router.post("/provider/switch")
def post_switch_provider(provider: str):
    from ..services.price_providers.service import switch_provider
    switch_provider(provider)
    from ..services.price_providers.service import get_price_service
    return {"status": "success", "new_provider": get_price_service().provider.name}

@router.get("/search-symbol")
def search_market_symbol(q: str):
    from ..services.market_data import search_ticker_by_name
    symbol = search_ticker_by_name(q)
    return {"query": q, "symbol": symbol}
