import sqlite3

# Connect to your database file
conn = sqlite3.connect("userdb")  # replace with your database filename
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

# Example: view all data in users table
cursor.execute("SELECT * FROM users;")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()