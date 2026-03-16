import yfinance as yf
from jugaad_data.nse import NSELive

def test_price():
    symbol = "NEWGEN"
    print(f"Testing {symbol}...")
    
    # 1. Jugaad
    try:
        nse = NSELive()
        quote = nse.stock_quote(symbol)
        price = quote['priceInfo']['lastPrice']
        print(f"Jugaad Price: {price}")
    except Exception as e:
        print(f"Jugaad failed: {e}")
        
    # 2. YFinance
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        price = ticker.fast_info.get('last_price')
        print(f"YFinance Price: {price}")
    except Exception as e:
        print(f"YFinance failed: {e}")

if __name__ == "__main__":
    test_price()
