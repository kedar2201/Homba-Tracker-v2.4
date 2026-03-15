from app.services.price_providers.jugaad_provider import JugaadNSEProvider

def test_jugaad_fetch():
    provider = JugaadNSEProvider()
    symbol = "NSE:SGBSEP31II"
    print(f"Testing fetch for symbol: {symbol}")
    # Note: JugaadNSEProvider handles prefixes
    results = provider.fetch_prices([symbol])
    print(f"Results: {results}")

if __name__ == "__main__":
    test_jugaad_fetch()
