from jugaad_data.nse import NSELive
import json
from datetime import datetime

def test_live_data():
    n = NSELive()
    print(f"Testing Live NSE Data at {datetime.now()}...")
    
    # 1. Test Index (NIFTY 50)
    try:
        all_indices = n.all_indices()
        nifty = next((x for x in all_indices['data'] if x['index'] == "NIFTY 50"), None)
        if nifty:
            print(f"\nNIFTY 50 (Live):")
            print(f"  Price: {nifty['last']}")
            print(f"  Change: {nifty['variation']} ({nifty['percentChange']}%)")
            print(f"  Prev Close: {nifty['previousClose']}")
        else:
            print("\nNIFTY 50 not found in index data.")
    except Exception as e:
        print(f"\nError fetching index: {e}")

    # 2. Test Stock (RELIANCE)
    try:
        stock_data = n.stock_quote("RELIANCE")
        price_info = stock_data['priceInfo']
        metadata = stock_data['metadata']
        print(f"\nRELIANCE (Live):")
        print(f"  Symbol: {metadata['symbol']}")
        print(f"  Price: {price_info['lastPrice']}")
        print(f"  Change: {price_info['change']} ({round(price_info['pChange'], 2)}%)")
        print(f"  Prev Close: {price_info['previousClose']}")
    except Exception as e:
        print(f"\nError fetching stock: {e}")

if __name__ == "__main__":
    test_live_data()
