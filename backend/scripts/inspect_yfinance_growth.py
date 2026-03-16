
import yfinance as yf
import json

def inspect_stock(symbol):
    print(f"Fetching info for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Keys of interest based on user request
        keys_to_check = [
            'currentPrice',
            'trailingEps',
            'forwardEps',
            'earningsGrowth',
            'growthEstimates', # might not exist directly
            'pegRatio',
            'trailingPE',
            'forwardPE'
        ]
        
        filtered_info = {k: info.get(k) for k in keys_to_check}
        
        # Look for anything resembling "growth" or "estimates"
        growth_keys = [k for k in info.keys() if 'growth' in k.lower() or 'estim' in k.lower()]
        
        print("\n--- Requested Fields Data ---")
        print(json.dumps(filtered_info, indent=2))
        
        print("\n--- All Growth/Estimate Related Keys ---")
        for k in growth_keys:
            print(f"{k}: {info[k]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_stock("RELIANCE.NS")
