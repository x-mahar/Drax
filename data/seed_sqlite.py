# data/seed.py

import sqlite3
import os
from data.generate_big_data import generate_big_data

DB_PATH = os.path.join(os.path.dirname(__file__), "../sales.db")

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            region TEXT,
            product TEXT,
            revenue REAL,
            customer_name TEXT
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM sales")

    # Generate & insert 10k rows
    data = generate_big_data(10000)
    cursor.executemany("""
        INSERT INTO sales (date, region, product, revenue, customer_name)
        VALUES (:date, :region, :product, :revenue, :customer_name)
    """, data)

    conn.commit()
    conn.close()
    print(f"✅ SQLite seeded with {len(data)} rows!")

if __name__ == "__main__":
    seed()