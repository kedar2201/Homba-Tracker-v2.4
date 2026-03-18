import yfinance as yf
import time

def test_yfinance():
    symbol = "RELIANCE.NS"
    print(f"Fetching history for {symbol}...")
    start = time.time()
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        duration = time.time() - start
        print(f"Fetch complete in {duration:.2f}s")
        if not hist.empty:
            print("Row count:", len(hist))
            print("Last close:", hist['Close'].iloc[-1])
        else:
            print("Empty history")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yfinance()
