# data/seed_mysql.py

import mysql.connector
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
from data.generate_big_data import generate_big_data

def seed():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date TEXT,
            region TEXT,
            product TEXT,
            revenue FLOAT,
            customer_name TEXT
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM sales")

    # Generate & insert 10k rows
    data = generate_big_data(10000)

    # Convert dicts to tuples for MySQL
    rows = [(d["date"], d["region"], d["product"], d["revenue"], d["customer_name"]) for d in data]

    cursor.executemany("""
        INSERT INTO sales (date, region, product, revenue, customer_name)
        VALUES (%s, %s, %s, %s, %s)
    """, rows)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ MySQL seeded with {len(data)} rows!")

if __name__ == "__main__":
    seed()