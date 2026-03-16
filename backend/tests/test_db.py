import sqlite3

conn = sqlite3.connect('financial_portfolio.db')
cursor = conn.cursor()

# Get users
cursor.execute("SELECT id, username FROM users")
users = cursor.fetchall()
print("Users:", users)

# Get radar_scoring_weights
cursor.execute("SELECT * FROM radar_scoring_weights")
configs = cursor.fetchall()
print("\nRadar Configs:", configs)

# Get tracklist items
cursor.execute("SELECT id, user_id, symbol FROM tracklists")
items = cursor.fetchall()
print("\nTracklist Items:", items)

conn.close()
