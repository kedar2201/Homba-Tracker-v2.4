from app.services.market_data import fetch_live_stock_prices
import pandas as pd

symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
prices = fetch_live_stock_prices(symbols)
print("Prices:", prices)

from app.services.market_data import fetch_mf_nav
nav = fetch_mf_nav("122639") # Parag Parikh Flexi
print("MF NAV:", nav)
