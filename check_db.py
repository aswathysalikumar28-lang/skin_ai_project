import sqlite3

conn = sqlite3.connect("userdb.db")
cursor = conn.cursor()

for row in cursor.execute("SELECT * FROM skin_pattern"):
    print(row)

conn.close()