from app.services.price_providers.yfinance_provider import YFinanceProvider

def test_sgb_fetch():
    provider = YFinanceProvider()
    symbol = "NSE:SGBSEP31II.NS"
    print(f"Testing fetch for symbol: {symbol}")
    results = provider.fetch_prices([symbol])
    print(f"Results: {results}")

if __name__ == "__main__":
    test_sgb_fetch()
