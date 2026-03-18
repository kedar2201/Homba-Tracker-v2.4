from app.services.price_providers.service import price_service
from app.database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)

symbols = ["NSE:INFY", "BOM:500414", "AAPL"]
print(f"Fetching prices for {symbols}...")
prices = price_service.get_prices(symbols)
print(f"Results: {prices}")
