import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_analytics():
    print("Testing Analytics API...")
    
    # 1. Get a symbol to test (e.g., RELIANCE)
    symbol = "RELIANCE"
    print(f"Fetching analytics for {symbol}...")
    response = requests.get(f"{BASE_URL}/api/analytics/{symbol}")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Content: {response.text}")
    if response.status_code == 200:
        try:
            data = response.json()
            print("Analytics Data:", json.dumps(data, indent=2))
        except Exception as e:
            print(f"JSON Decode Error: {e}")
        
        # 2. Update EPS
        print(f"\nUpdating EPS for {symbol} to 150.0...")
        eps_response = requests.post(f"{BASE_URL}/api/analytics/eps", json={"symbol": symbol, "eps": 150.0})
        if eps_response.status_code == 200:
            print("EPS Update Success:", eps_response.json())
        else:
            print("EPS Update Failed:", eps_response.text)
            
        # 3. Refresh Analytics
        print(f"\nRefreshing Analytics for {symbol}...")
        refresh_response = requests.post(f"{BASE_URL}/api/analytics/refresh/{symbol}")
        if refresh_response.status_code == 200:
            print("Refresh Success:", refresh_response.json())
        else:
            print("Refresh Failed:", refresh_response.text)
            
    else:
        print("Failed to fetch analytics:", response.text)

if __name__ == "__main__":
    test_analytics()
