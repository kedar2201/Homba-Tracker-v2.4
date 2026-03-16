import requests

url_base = 'http://127.0.0.1:8000/api/auth'

# Register
try:
    requests.post(f"{url_base}/register", json={'email':'t2@t.com','username':'t2','mobile_number':'1234','password':'p'})
except Exception as e:
    print(e)

# Login
r = requests.post(f"{url_base}/token", data={'username':'t2','password':'p'})
print("Login:", r.status_code, r.text)
token = r.json().get('access_token')

# Add tracklist
r2 = requests.post(f"{url_base}/tracklist", headers={'Authorization': f'Bearer {token}'}, json={
    "symbol": "NEWGEN",
    "target_price": "500"
})
print("Add item:", r2.status_code, r2.text)

# Get tracklist
r3 = requests.get(f"{url_base}/tracklist", headers={'Authorization': f'Bearer {token}'})
print("Get items:", r3.status_code, r3.text)
