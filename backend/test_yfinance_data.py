import yfinance as yf
import json

def check_stock_data():
    # symbols = ["RELIANCE.NS", "AHLUCONT.NS", "TCS.NS"]
    symbols = ["AHLUCONT.NS"]
    
    for symbol in symbols:
        print(f"\n--- Checking {symbol} ---")
        try:
            ticker = yf.Ticker(symbol)
            
            # 1. Price from fast_info (usually faster/reliable for latest price)
            try:
                price = ticker.fast_info['last_price']
                print(f"FastInfo Price: {price}")
            except Exception as e:
                print(f"FastInfo Error: {e}")
                
            # 2. EPS from info
            try:
                info = ticker.info
                trailing_eps = info.get('trailingEps')
                forward_eps = info.get('forwardEps')
                print(f"Trailing EPS: {trailing_eps}")
                print(f"Forward EPS: {forward_eps}")
                print(f"PE Ratio (from info): {info.get('trailingPE')}")
            except Exception as e:
                print(f"Info/EPS Error: {e}")
                
        except Exception as e:
            print(f"Ticker Error: {e}")

if __name__ == "__main__":
    check_stock_data()
