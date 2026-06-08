# data/seed_mysql_retail.py
# creates all 15 tables + seeds them

import mysql.connector
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
from data.generate_retail_data import generate_retail_data


def seed(n_orders: int = 1000):
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    cursor = conn.cursor()

    # ── DROP existing retail tables (clean slate) ─────────────
    # Disable FK checks so we can drop in any order
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for table in [
        "store_sales", "payments", "returns", "order_items", "orders",
        "employees", "stores", "departments", "inventory", "warehouses",
        "products", "customers", "brands", "categories", "customer_segments"
    ]:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    print("🗑️  Dropped existing retail tables.")

    # ── CREATE tables ─────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE customer_segments (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            segment_name  VARCHAR(50)   NOT NULL,
            discount_rate DECIMAL(4,2)  NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE categories (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL,
            department    VARCHAR(100) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE brands (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            brand_name VARCHAR(100) NOT NULL,
            country    VARCHAR(100) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE customers (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(150) NOT NULL,
            email      VARCHAR(150),
            phone      VARCHAR(20),
            city       VARCHAR(100),
            region     VARCHAR(50),
            segment_id INT,
            FOREIGN KEY (segment_id) REFERENCES customer_segments(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(150) NOT NULL,
            category_id INT,
            brand_id    INT,
            price       DECIMAL(10,2) NOT NULL,
            sku         VARCHAR(50),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (brand_id)    REFERENCES brands(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE warehouses (
            id     INT AUTO_INCREMENT PRIMARY KEY,
            name   VARCHAR(150) NOT NULL,
            city   VARCHAR(100),
            region VARCHAR(50)
        )
    """)

    cursor.execute("""
        CREATE TABLE inventory (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            product_id    INT,
            warehouse_id  INT,
            stock_qty     INT          NOT NULL DEFAULT 0,
            reorder_level INT          NOT NULL DEFAULT 10,
            FOREIGN KEY (product_id)   REFERENCES products(id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE departments (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            department_name VARCHAR(100) NOT NULL,
            manager_id      INT          -- FK added after employees
        )
    """)

    cursor.execute("""
        CREATE TABLE stores (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(150) NOT NULL,
            city       VARCHAR(100),
            region     VARCHAR(50),
            store_type VARCHAR(50)
        )
    """)

    cursor.execute("""
        CREATE TABLE employees (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(150) NOT NULL,
            role          VARCHAR(100),
            department_id INT,
            store_id      INT,
            salary        DECIMAL(10,2),
            FOREIGN KEY (department_id) REFERENCES departments(id),
            FOREIGN KEY (store_id)      REFERENCES stores(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT,
            order_date  DATE NOT NULL,
            status      VARCHAR(50),
            channel     VARCHAR(50),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE order_items (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            order_id   INT,
            product_id INT,
            quantity   INT           NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            discount   DECIMAL(4,2)  DEFAULT 0,
            FOREIGN KEY (order_id)   REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE returns (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            order_item_id INT,
            return_date   DATE,
            reason        VARCHAR(150),
            FOREIGN KEY (order_item_id) REFERENCES order_items(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE payments (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            order_id     INT,
            payment_date DATE,
            method       VARCHAR(50),
            amount       DECIMAL(10,2),
            status       VARCHAR(50),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE store_sales (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            store_id   INT,
            product_id INT,
            sale_date  DATE,
            quantity   INT,
            revenue    DECIMAL(10,2),
            FOREIGN KEY (store_id)   REFERENCES stores(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    print("✅ Created 15 retail tables.")

    # ── GENERATE data ─────────────────────────────────────────
    print(f"⏳ Generating retail data ({n_orders} orders)...")
    data = generate_retail_data(n_orders)

    # ── INSERT — parent tables first ──────────────────────────

    cursor.executemany(
        "INSERT INTO customer_segments (id, segment_name, discount_rate) VALUES (%s, %s, %s)",
        [(r["id"], r["segment_name"], r["discount_rate"]) for r in data["customer_segments"]]
    )

    cursor.executemany(
        "INSERT INTO categories (id, category_name, department) VALUES (%s, %s, %s)",
        [(r["id"], r["category_name"], r["department"]) for r in data["categories"]]
    )

    cursor.executemany(
        "INSERT INTO brands (id, brand_name, country) VALUES (%s, %s, %s)",
        [(r["id"], r["brand_name"], r["country"]) for r in data["brands"]]
    )

    cursor.executemany(
        "INSERT INTO customers (id, name, email, phone, city, region, segment_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        [(r["id"], r["name"], r["email"], r["phone"], r["city"], r["region"], r["segment_id"])
         for r in data["customers"]]
    )

    cursor.executemany(
        "INSERT INTO products (id, name, category_id, brand_id, price, sku) VALUES (%s, %s, %s, %s, %s, %s)",
        [(r["id"], r["name"], r["category_id"], r["brand_id"], r["price"], r["sku"])
         for r in data["products"]]
    )

    cursor.executemany(
        "INSERT INTO warehouses (id, name, city, region) VALUES (%s, %s, %s, %s)",
        [(r["id"], r["name"], r["city"], r["region"]) for r in data["warehouses"]]
    )

    cursor.executemany(
        "INSERT INTO inventory (id, product_id, warehouse_id, stock_qty, reorder_level) VALUES (%s, %s, %s, %s, %s)",
        [(r["id"], r["product_id"], r["warehouse_id"], r["stock_qty"], r["reorder_level"])
         for r in data["inventory"]]
    )

    cursor.executemany(
        "INSERT INTO departments (id, department_name, manager_id) VALUES (%s, %s, %s)",
        [(r["id"], r["department_name"], r["manager_id"]) for r in data["departments"]]
    )

    cursor.executemany(
        "INSERT INTO stores (id, name, city, region, store_type) VALUES (%s, %s, %s, %s, %s)",
        [(r["id"], r["name"], r["city"], r["region"], r["store_type"]) for r in data["stores"]]
    )

    cursor.executemany(
        "INSERT INTO employees (id, name, role, department_id, store_id, salary) VALUES (%s, %s, %s, %s, %s, %s)",
        [(r["id"], r["name"], r["role"], r["department_id"], r["store_id"], r["salary"])
         for r in data["employees"]]
    )

    # Add FK on departments.manager_id now that employees exist
    cursor.execute("""
        ALTER TABLE departments
        ADD CONSTRAINT fk_dept_manager
        FOREIGN KEY (manager_id) REFERENCES employees(id)
    """)

    cursor.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status, channel) VALUES (%s, %s, %s, %s, %s)",
        [(r["id"], r["customer_id"], r["order_date"], r["status"], r["channel"])
         for r in data["orders"]]
    )

    cursor.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount) VALUES (%s, %s, %s, %s, %s, %s)",
        [(r["id"], r["order_id"], r["product_id"], r["quantity"], r["unit_price"], r["discount"])
         for r in data["order_items"]]
    )

    cursor.executemany(
        "INSERT INTO returns (id, order_item_id, return_date, reason) VALUES (%s, %s, %s, %s)",
        [(r["id"], r["order_item_id"], r["return_date"], r["reason"])
         for r in data["returns"]]
    )

    cursor.executemany(
        "INSERT INTO payments (id, order_id, payment_date, method, amount, status) VALUES (%s, %s, %s, %s, %s, %s)",
        [(r["id"], r["order_id"], r["payment_date"], r["method"], r["amount"], r["status"])
         for r in data["payments"]]
    )

    cursor.executemany(
        "INSERT INTO store_sales (id, store_id, product_id, sale_date, quantity, revenue) VALUES (%s, %s, %s, %s, %s, %s)",
        [(r["id"], r["store_id"], r["product_id"], r["sale_date"], r["quantity"], r["revenue"])
         for r in data["store_sales"]]
    )

    conn.commit()
    cursor.close()
    conn.close()

    # ── Summary ───────────────────────────────────────────────
    print("\n✅ MySQL retail schema seeded successfully!")
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