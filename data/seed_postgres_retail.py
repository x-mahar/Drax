# data/seed_postgres_retail.py
# creates all 15 tables + seeds them

import psycopg2
from psycopg2.extras import execute_values
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
from data.generate_retail_data import generate_retail_data


def seed(n_orders: int = 1000):
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()

    # ── DROP existing retail tables (clean slate) ─────────────
    # Order matters — child tables first to respect FK constraints
    cursor.execute("""
        DROP TABLE IF EXISTS
            store_sales, payments, returns, order_items, orders,
            employees, stores, departments, inventory, warehouses,
            products, customers, brands, categories, customer_segments
        CASCADE;
    """)
    print("🗑️  Dropped existing retail tables.")

    # ── CREATE tables ─────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE customer_segments (
            id            SERIAL PRIMARY KEY,
            segment_name  VARCHAR(50)  NOT NULL,
            discount_rate NUMERIC(4,2) NOT NULL
        );

        CREATE TABLE categories (
            id            SERIAL PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL,
            department    VARCHAR(100) NOT NULL
        );

        CREATE TABLE brands (
            id         SERIAL PRIMARY KEY,
            brand_name VARCHAR(100) NOT NULL,
            country    VARCHAR(100) NOT NULL
        );

        CREATE TABLE customers (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(150) NOT NULL,
            email      VARCHAR(150),
            phone      VARCHAR(20),
            city       VARCHAR(100),
            region     VARCHAR(50),
            segment_id INT REFERENCES customer_segments(id)
        );

        CREATE TABLE products (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(150) NOT NULL,
            category_id INT REFERENCES categories(id),
            brand_id    INT REFERENCES brands(id),
            price       NUMERIC(10,2) NOT NULL,
            sku         VARCHAR(50)
        );

        CREATE TABLE warehouses (
            id     SERIAL PRIMARY KEY,
            name   VARCHAR(150) NOT NULL,
            city   VARCHAR(100),
            region VARCHAR(50)
        );

        CREATE TABLE inventory (
            id            SERIAL PRIMARY KEY,
            product_id    INT REFERENCES products(id),
            warehouse_id  INT REFERENCES warehouses(id),
            stock_qty     INT NOT NULL DEFAULT 0,
            reorder_level INT NOT NULL DEFAULT 10
        );

        CREATE TABLE departments (
            id              SERIAL PRIMARY KEY,
            department_name VARCHAR(100) NOT NULL,
            manager_id      INT          -- FK added after employees
        );

        CREATE TABLE stores (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(150) NOT NULL,
            city       VARCHAR(100),
            region     VARCHAR(50),
            store_type VARCHAR(50)
        );

        CREATE TABLE employees (
            id            SERIAL PRIMARY KEY,
            name          VARCHAR(150) NOT NULL,
            role          VARCHAR(100),
            department_id INT REFERENCES departments(id),
            store_id      INT REFERENCES stores(id),
            salary        NUMERIC(10,2)
        );

        CREATE TABLE orders (
            id          SERIAL PRIMARY KEY,
            customer_id INT REFERENCES customers(id),
            order_date  DATE NOT NULL,
            status      VARCHAR(50),
            channel     VARCHAR(50)
        );

        CREATE TABLE order_items (
            id         SERIAL PRIMARY KEY,
            order_id   INT REFERENCES orders(id),
            product_id INT REFERENCES products(id),
            quantity   INT           NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL,
            discount   NUMERIC(4,2)  DEFAULT 0
        );

        CREATE TABLE returns (
            id            SERIAL PRIMARY KEY,
            order_item_id INT REFERENCES order_items(id),
            return_date   DATE,
            reason        VARCHAR(150)
        );

        CREATE TABLE payments (
            id           SERIAL PRIMARY KEY,
            order_id     INT REFERENCES orders(id),
            payment_date DATE,
            method       VARCHAR(50),
            amount       NUMERIC(10,2),
            status       VARCHAR(50)
        );

        CREATE TABLE store_sales (
            id         SERIAL PRIMARY KEY,
            store_id   INT REFERENCES stores(id),
            product_id INT REFERENCES products(id),
            sale_date  DATE,
            quantity   INT,
            revenue    NUMERIC(10,2)
        );
    """)
    print("✅ Created 15 retail tables.")

    # ── GENERATE data ─────────────────────────────────────────
    print(f"⏳ Generating retail data ({n_orders} orders)...")
    data = generate_retail_data(n_orders)

    # ── INSERT — parent tables first ──────────────────────────

    execute_values(cursor,
        "INSERT INTO customer_segments (id, segment_name, discount_rate) VALUES %s",
        [(r["id"], r["segment_name"], r["discount_rate"]) for r in data["customer_segments"]]
    )

    execute_values(cursor,
        "INSERT INTO categories (id, category_name, department) VALUES %s",
        [(r["id"], r["category_name"], r["department"]) for r in data["categories"]]
    )

    execute_values(cursor,
        "INSERT INTO brands (id, brand_name, country) VALUES %s",
        [(r["id"], r["brand_name"], r["country"]) for r in data["brands"]]
    )

    execute_values(cursor,
        "INSERT INTO customers (id, name, email, phone, city, region, segment_id) VALUES %s",
        [(r["id"], r["name"], r["email"], r["phone"], r["city"], r["region"], r["segment_id"])
         for r in data["customers"]]
    )

    execute_values(cursor,
        "INSERT INTO products (id, name, category_id, brand_id, price, sku) VALUES %s",
        [(r["id"], r["name"], r["category_id"], r["brand_id"], r["price"], r["sku"])
         for r in data["products"]]
    )

    execute_values(cursor,
        "INSERT INTO warehouses (id, name, city, region) VALUES %s",
        [(r["id"], r["name"], r["city"], r["region"]) for r in data["warehouses"]]
    )

    execute_values(cursor,
        "INSERT INTO inventory (id, product_id, warehouse_id, stock_qty, reorder_level) VALUES %s",
        [(r["id"], r["product_id"], r["warehouse_id"], r["stock_qty"], r["reorder_level"])
         for r in data["inventory"]]
    )

    execute_values(cursor,
        "INSERT INTO departments (id, department_name, manager_id) VALUES %s",
        [(r["id"], r["department_name"], r["manager_id"]) for r in data["departments"]]
    )

    execute_values(cursor,
        "INSERT INTO stores (id, name, city, region, store_type) VALUES %s",
        [(r["id"], r["name"], r["city"], r["region"], r["store_type"]) for r in data["stores"]]
    )

    execute_values(cursor,
        "INSERT INTO employees (id, name, role, department_id, store_id, salary) VALUES %s",
        [(r["id"], r["name"], r["role"], r["department_id"], r["store_id"], r["salary"])
         for r in data["employees"]]
    )

    # Add FK on departments.manager_id now that employees exist
    cursor.execute("""
        ALTER TABLE departments
        ADD CONSTRAINT fk_dept_manager
        FOREIGN KEY (manager_id) REFERENCES employees(id);
    """)

    execute_values(cursor,
        "INSERT INTO orders (id, customer_id, order_date, status, channel) VALUES %s",
        [(r["id"], r["customer_id"], r["order_date"], r["status"], r["channel"])
         for r in data["orders"]]
    )

    execute_values(cursor,
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount) VALUES %s",
        [(r["id"], r["order_id"], r["product_id"], r["quantity"], r["unit_price"], r["discount"])
         for r in data["order_items"]]
    )

    execute_values(cursor,
        "INSERT INTO returns (id, order_item_id, return_date, reason) VALUES %s",
        [(r["id"], r["order_item_id"], r["return_date"], r["reason"])
         for r in data["returns"]]
    )

    execute_values(cursor,
        "INSERT INTO payments (id, order_id, payment_date, method, amount, status) VALUES %s",
        [(r["id"], r["order_id"], r["payment_date"], r["method"], r["amount"], r["status"])
         for r in data["payments"]]
    )

    execute_values(cursor,
        "INSERT INTO store_sales (id, store_id, product_id, sale_date, quantity, revenue) VALUES %s",
        [(r["id"], r["store_id"], r["product_id"], r["sale_date"], r["quantity"], r["revenue"])
         for r in data["store_sales"]]
    )

    conn.commit()
    cursor.close()
    conn.close()

    # ── Summary ───────────────────────────────────────────────
    print("\n✅ PostgreSQL retail schema seeded successfully!")
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