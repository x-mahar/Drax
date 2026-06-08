# data/seed_postgres.py

import psycopg2
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
from data.generate_big_data import generate_big_data

def seed():
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM sales")

    # Generate & insert 10k rows
    data = generate_big_data(10000)
    cursor.executemany("""
        INSERT INTO sales (date, region, product, revenue, customer_name)
        VALUES (%(date)s, %(region)s, %(product)s, %(revenue)s, %(customer_name)s)
    """, data)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ PostgreSQL seeded with {len(data)} rows!")

if __name__ == "__main__":
    seed()