import sqlite3

# Connect to fresh database
conn = sqlite3.connect("userdb.db")
cursor = conn.cursor()

# ------------------------
# Users table
# ------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# ------------------------
# Skin pattern table (must match Flask routes)
# ------------------------
cursor.execute("""
CREATE TABLE skin_pattern (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    cycle_start_date TEXT NOT NULL,
    cycle_end_date TEXT NOT NULL,
    cycle_day INTEGER NOT NULL,
    pimples INTEGER NOT NULL,
    pimple_occurrence TEXT NOT NULL,
    sleep_hours REAL NOT NULL,
    water_glasses REAL NOT NULL
)
""")

# ------------------------
# Optional advanced logs table
# ------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS skin_cycle_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    log_date DATE NOT NULL,
    cycle_start_date DATE,
    cycle_end_date DATE,
    cycle_day INTEGER,
    pimple_count INTEGER,
    pimple_timing TEXT,
    pimple_area TEXT,
    sleep_hours REAL,
    water_glasses INTEGER,
    stress_level INTEGER,
    diet_type TEXT,
    skincare_used TEXT,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

conn.commit()
conn.close()
print("Fresh database created successfully!")