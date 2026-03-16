import requests
import sys

def verify_growth():
    try:
        # Assuming dev user ID 1
        # We need to authenticate or mock... backend has Depends(get_current_user)
        # Actually, let's just use the `debug_nav_api.py` approach but for /growth
        # But /growth requires auth.
        # Let's import the function and run it directly in a shell context?
        # No, easier to just use the existing test pattern if possible.
        
        # We can use the FastApi TestClient
        from fastapi.testclient import TestClient
        from app.main import app
        from app.routers import dashboard
        from app.services.market_data import set_cached_value
        
        # Clear cache to force new logic
        # dashboard.cache_key will be v9..._1
        # But we can just call the function directly if we mock dependencies
        
        client = TestClient(app)
        
        # Mock auth? The app has a mock login for dev typically or we can override dependency
        from app.dependencies import get_current_user
        from app.models.user import User
        
        def mock_get_current_user():
            return User(id=1, email="test@test.com", is_active=True)
            
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        # Call API
        response = client.get("/api/dashboard/growth")
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} {response.text}")
            return
            
        data = response.json()
        if not data:
            print("No data returned!")
            return
            
        last_entry = data[-1]
        print(f"Data Length: {len(data)}")
        print(f"First Entry: {data[0]}")
        print(f"Last Entry: {last_entry}")
        
        p_val = last_entry.get("portfolio_val")
        print(f"Latest Portfolio Value: {p_val}")
        
        if p_val > 100000000: # > 10 Cr
            print("SUCCESS: Portfolio Value is in correct magnitude (> 10Cr)")
        else:
            print("FAILURE: Portfolio Value is too low (likely Equity only)")
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_growth()
