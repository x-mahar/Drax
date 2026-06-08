# data/seed_sqlite_retail.py
# creates all 15 tables + seeds them

import sqlite3
import os
from data.generate_retail_data import generate_retail_data

DB_PATH = os.path.join(os.path.dirname(__file__), "../retail.db")


def seed(n_orders: int = 1000):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── DROP existing retail tables (clean slate) ─────────────
    # Order matters — child tables first to respect FK constraints
    cursor.executescript("""
        PRAGMA foreign_keys = OFF;

        DROP TABLE IF EXISTS store_sales;
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS returns;
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS employees;
        DROP TABLE IF EXISTS stores;
        DROP TABLE IF EXISTS departments;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS warehouses;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS brands;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS customer_segments;

        PRAGMA foreign_keys = ON;
    """)
    print("🗑️  Dropped existing retail tables.")

    # ── CREATE tables ─────────────────────────────────────────

    cursor.executescript("""
        CREATE TABLE customer_segments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_name  TEXT    NOT NULL,
            discount_rate REAL    NOT NULL
        );

        CREATE TABLE categories (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL,
            department    TEXT NOT NULL
        );

        CREATE TABLE brands (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL,
            country    TEXT NOT NULL
        );

        CREATE TABLE customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT,
            phone      TEXT,
            city       TEXT,
            region     TEXT,
            segment_id INTEGER REFERENCES customer_segments(id)
        );

        CREATE TABLE products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            brand_id    INTEGER REFERENCES brands(id),
            price       REAL    NOT NULL,
            sku         TEXT
        );

        CREATE TABLE warehouses (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            city   TEXT,
            region TEXT
        );

        CREATE TABLE inventory (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id    INTEGER REFERENCES products(id),
            warehouse_id  INTEGER REFERENCES warehouses(id),
            stock_qty     INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 10
        );

        CREATE TABLE departments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT NOT NULL,
            manager_id      INTEGER
        );

        CREATE TABLE stores (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            city       TEXT,
            region     TEXT,
            store_type TEXT
        );

        CREATE TABLE employees (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            role          TEXT,
            department_id INTEGER REFERENCES departments(id),
            store_id      INTEGER REFERENCES stores(id),
            salary        REAL
        );

        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER REFERENCES customers(id),
            order_date  TEXT    NOT NULL,
            status      TEXT,
            channel     TEXT
        );

        CREATE TABLE order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER REFERENCES orders(id),
            product_id INTEGER REFERENCES products(id),
            quantity   INTEGER NOT NULL,
            unit_price REAL    NOT NULL,
            discount   REAL    DEFAULT 0
        );

        CREATE TABLE returns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_item_id INTEGER REFERENCES order_items(id),
            return_date   TEXT,
            reason        TEXT
        );

        CREATE TABLE payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER REFERENCES orders(id),
            payment_date TEXT,
            method       TEXT,
            amount       REAL,
            status       TEXT
        );

        CREATE TABLE store_sales (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id   INTEGER REFERENCES stores(id),
            product_id INTEGER REFERENCES products(id),
            sale_date  TEXT,
            quantity   INTEGER,
            revenue    REAL
        );
    """)
    print("✅ Created 15 retail tables.")

    # ── GENERATE data ─────────────────────────────────────────
    print(f"⏳ Generating retail data ({n_orders} orders)...")
    data = generate_retail_data(n_orders)

    # ── INSERT — parent tables first ──────────────────────────

    cursor.executemany(
        "INSERT INTO customer_segments (id, segment_name, discount_rate) VALUES (:id, :segment_name, :discount_rate)",
        data["customer_segments"]
    )

    cursor.executemany(
        "INSERT INTO categories (id, category_name, department) VALUES (:id, :category_name, :department)",
        data["categories"]
    )

    cursor.executemany(
        "INSERT INTO brands (id, brand_name, country) VALUES (:id, :brand_name, :country)",
        data["brands"]
    )

    cursor.executemany(
        "INSERT INTO customers (id, name, email, phone, city, region, segment_id) VALUES (:id, :name, :email, :phone, :city, :region, :segment_id)",
        data["customers"]
    )

    cursor.executemany(
        "INSERT INTO products (id, name, category_id, brand_id, price, sku) VALUES (:id, :name, :category_id, :brand_id, :price, :sku)",
        data["products"]
    )

    cursor.executemany(
        "INSERT INTO warehouses (id, name, city, region) VALUES (:id, :name, :city, :region)",
        data["warehouses"]
    )

    cursor.executemany(
        "INSERT INTO inventory (id, product_id, warehouse_id, stock_qty, reorder_level) VALUES (:id, :product_id, :warehouse_id, :stock_qty, :reorder_level)",
        data["inventory"]
    )

    cursor.executemany(
        "INSERT INTO departments (id, department_name, manager_id) VALUES (:id, :department_name, :manager_id)",
        data["departments"]
    )

    cursor.executemany(
        "INSERT INTO stores (id, name, city, region, store_type) VALUES (:id, :name, :city, :region, :store_type)",
        data["stores"]
    )

    cursor.executemany(
        "INSERT INTO employees (id, name, role, department_id, store_id, salary) VALUES (:id, :name, :role, :department_id, :store_id, :salary)",
        data["employees"]
    )

    # Add FK on departments.manager_id now that employees exist
    # SQLite doesn't support ALTER TABLE ADD CONSTRAINT — update directly instead
    cursor.executemany(
        "UPDATE departments SET manager_id = :manager_id WHERE id = :id",
        [{"id": r["id"], "manager_id": r["manager_id"]} for r in data["departments"]]
    )

    cursor.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status, channel) VALUES (:id, :customer_id, :order_date, :status, :channel)",
        data["orders"]
    )

    cursor.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount) VALUES (:id, :order_id, :product_id, :quantity, :unit_price, :discount)",
        data["order_items"]
    )

    cursor.executemany(
        "INSERT INTO returns (id, order_item_id, return_date, reason) VALUES (:id, :order_item_id, :return_date, :reason)",
        data["returns"]
    )

    cursor.executemany(
        "INSERT INTO payments (id, order_id, payment_date, method, amount, status) VALUES (:id, :order_id, :payment_date, :method, :amount, :status)",
        data["payments"]
    )

    cursor.executemany(
        "INSERT INTO store_sales (id, store_id, product_id, sale_date, quantity, revenue) VALUES (:id, :store_id, :product_id, :sale_date, :quantity, :revenue)",
        data["store_sales"]
    )

    conn.commit()
    cursor.close()
    conn.close()

    # ── Summary ───────────────────────────────────────────────
    print("\n✅ SQLite retail schema seeded successfully!")
    print(f"   customer_segments : {len(data['customer_segments'])}")
    print(f"   categories        : {len(data['categories'])}")
    print(f"   brands            : {len(data['brands'])}")
    print(f"   customers         : {len(data['customers'])}")
    print(f"   products          : {len(data['products'])}")
    print(f"   warehouses        : {len(data['warehouses'])}")
    print(f"   inventory         : {len(data['inventory'])}")
    print(f"   departments       : {len(data['departments'])}")
    print(f"   stores            : {len(data['stores'])}")
    print(f"   employees         : {len(data['employees'])}")
    print(f"   orders            : {len(data['orders'])}")
    print(f"   order_items       : {len(data['order_items'])}")
    print(f"   returns           : {len(data['returns'])}")
    print(f"   payments          : {len(data['payments'])}")
    print(f"   store_sales       : {len(data['store_sales'])}")


if __name__ == "__main__":
    seed(n_orders=1000)  # change this number to scale up