import sqlite3
import os

db_path = "c:/Users/georg/Desktop/AlphaTrade Capital Bot/database/alphatrade.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    print(f"--- Table: {table} ---")
    cursor.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    for row in rows:
        row_str = " | ".join(map(str, row))
        if "USDT" in row_str.upper():
            print(row_str)

conn.close()
