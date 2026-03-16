import requests
import json
import sqlite3
import os
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api/auth"

def check_db(username):
    conn = sqlite3.connect('financial_portfolio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, license_status, is_verified, trial_end_at FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def test_admin_flow():
    print("--- STARTING SYSTEM SELF-TEST ---")
    
    # 1. LOGIN
    print("\n[Step 1] Logging in as admin...")
    login_res = requests.post(f"{BASE_URL}/token", data={"username": "testuser1", "password": "admin123"})
    if login_res.status_code != 200:
        print(f"FAILED LOGIN: {login_res.text}")
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login SUCCESS.")

    # 2. BLOCK GUEST
    print("\n[Step 2] Blocking user 'guest'...")
    block_res = requests.post(f"{BASE_URL}/update-license", 
                             json={"username": "guest", "status": "blocked"},
                             headers=headers)
    print(f"API Response status: {block_res.status_code}")
    try:
        print(f"API Response Body: {block_res.json()}")
    except:
        print(f"NO JSON in response: {block_res.text}")
        
    db_row = check_db("guest")
    print(f"DB Check (guest): {db_row}")
    if db_row[1] != 'blocked':
        print("ALERT: Status NOT changed to blocked in DB!")

    # 3. EXTEND T2 (30 Days)
    print("\n[Step 3] Extending 't2' for 30 days...")
    extend_res = requests.post(f"{BASE_URL}/update-license", 
                              json={"username": "t2", "status": "trial", "expiry_days": 30},
                              headers=headers)
    print(f"API Response status: {extend_res.status_code}")
    db_row = check_db("t2")
    print(f"DB Check (t2): {db_row}")
    if db_row[3] is None:
         print("ALERT: Expiry Date NOT set in DB!")

    # 4. ACTIVATE T2 (Permanent)
    print("\n[Step 4] Activating 't2' (Permanent)...")
    activate_res = requests.post(f"{BASE_URL}/activate", 
                               json={"username": "t2", "status": "active"},
                               headers=headers)
    print(f"API Response status: {activate_res.status_code}")
    db_row = check_db("t2")
    print(f"DB Check (t2): {db_row}")
    if db_row[1] != 'active' or db_row[3] is not None:
         print("ALERT: Activation or Expiry Reset FAILED in DB!")

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    test_admin_flow()
