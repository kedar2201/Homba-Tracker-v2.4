import requests

def debug_license():
    base_url = "http://127.0.0.1:8000/api/auth"
    
    # login
    login_data = { "username": "testuser1", "password": "testpassword1" } # assuming this is the pwd
    # Actually I don't know the password. Let's try to bypass auth by hitting the endpoint with a mock user if I can? 
    # No, I have to be the real user.
    
    # Alternative: check what's in the DB for is_verified carefully.
    import sqlite3
    conn = sqlite3.connect('financial_portfolio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, is_verified, is_admin, license_status FROM users WHERE username='testuser1'")
    print("DB Row:", cursor.fetchone())
    conn.close()

if __name__ == "__main__":
    debug_license()
