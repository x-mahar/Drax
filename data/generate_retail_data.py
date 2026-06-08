# data/generate_retail_data.py
#generates the fake retail data using Faker
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_IN")  # Indian locale for realistic retail data
random.seed(42)
Faker.seed(42)

# ── Master lists ──────────────────────────────────────────────

REGIONS   = ["North", "South", "East", "West", "Central"]
CHANNELS  = ["Online", "In-Store", "Mobile App", "Phone"]
METHODS   = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash", "EMI"]
ROLES     = ["Store Manager", "Sales Executive", "Cashier", "Inventory Manager", "HR Manager"]
DEPTS     = ["Sales", "Operations", "HR", "Finance", "Logistics"]
STORE_TYPES = ["Flagship", "Express", "Outlet", "Kiosk"]
RETURN_REASONS = ["Defective", "Wrong Item", "Size Issue", "Changed Mind", "Damaged in Transit"]
ORDER_STATUSES  = ["Completed", "Pending", "Cancelled", "Returned", "Processing"]
PAYMENT_STATUSES = ["Success", "Failed", "Pending", "Refunded"]

CATEGORIES = [
    ("Electronics",   "Technology"),
    ("Clothing",      "Fashion"),
    ("Footwear",      "Fashion"),
    ("Home & Kitchen","Home"),
    ("Sports",        "Lifestyle"),
    ("Beauty",        "Personal Care"),
    ("Toys",          "Kids"),
    ("Grocery",       "Food"),
]

BRANDS = [
    ("Samsung",  "South Korea"),
    ("Nike",     "USA"),
    ("Puma",     "Germany"),
    ("Lakme",    "India"),
    ("Prestige", "India"),
    ("Levi's",   "USA"),
    ("boAt",     "India"),
    ("Haier",    "China"),
    ("Bata",     "India"),
    ("Patanjali","India"),
]

PRODUCTS_BY_CATEGORY = {
    "Electronics":    [("Smartphone", 15000), ("Laptop", 45000), ("Earbuds", 2500),  ("Smart TV", 35000), ("Tablet", 20000)],
    "Clothing":       [("T-Shirt", 799),      ("Jeans", 1499),   ("Kurta", 999),      ("Jacket", 2999),    ("Saree", 1999)],
    "Footwear":       [("Running Shoes", 2499),("Sandals", 799),  ("Formal Shoes", 3499),("Sneakers", 1999),("Slippers", 399)],
    "Home & Kitchen": [("Mixer Grinder", 3499),("Pressure Cooker", 1299),("Bed Sheet", 899),("Curtains", 1199),("Water Bottle", 299)],
    "Sports":         [("Cricket Bat", 1499), ("Football", 799),  ("Yoga Mat", 599),   ("Dumbbells", 1299), ("Cycle", 8999)],
    "Beauty":         [("Face Wash", 299),    ("Lipstick", 499),  ("Moisturizer", 699),("Shampoo", 399),    ("Perfume", 1499)],
    "Toys":           [("Lego Set", 1999),    ("Board Game", 799),("Remote Car", 1299),("Doll", 599),       ("Puzzle", 399)],
    "Grocery":        [("Rice 5kg", 399),     ("Dal 1kg", 149),   ("Oil 1L", 199),     ("Biscuits", 99),    ("Tea 500g", 249)],
}

SEGMENT_NAMES = [
    ("Premium",   0.05),
    ("Regular",   0.10),
    ("Budget",    0.15),
    ("Wholesale", 0.20),
    ("Loyalty",   0.08),
]


def generate_retail_data(n_orders: int = 1000):
    """
    Generates all retail data as a dict of lists.
    n_orders controls the size — everything else scales from it.

    Returns:
    {
        "customer_segments": [...],
        "categories":        [...],
        "brands":            [...],
        "customers":         [...],
        "products":          [...],
        "warehouses":        [...],
        "inventory":         [...],
        "departments":       [...],
        "stores":            [...],
        "employees":         [...],
        "orders":            [...],
        "order_items":       [...],
        "returns":           [...],
        "payments":          [...],
        "store_sales":       [...],
    }
    """

    # ── 1. customer_segments ─────────────────────────────────
    customer_segments = [
        {"id": i + 1, "segment_name": name, "discount_rate": rate}
        for i, (name, rate) in enumerate(SEGMENT_NAMES)
    ]

    # ── 2. categories ────────────────────────────────────────
    categories = [
        {"id": i + 1, "category_name": cat, "department": dept}
        for i, (cat, dept) in enumerate(CATEGORIES)
    ]
    cat_name_to_id = {c["category_name"]: c["id"] for c in categories}

    # ── 3. brands ────────────────────────────────────────────
    brands = [
        {"id": i + 1, "brand_name": name, "country": country}
        for i, (name, country) in enumerate(BRANDS)
    ]

    # ── 4. customers ─────────────────────────────────────────
    n_customers = max(100, n_orders // 5)
    customers = []
    for i in range(n_customers):
        customers.append({
            "id":         i + 1,
            "name":       fake.name(),
            "email":      fake.email(),
            "phone":      fake.phone_number()[:15],
            "city":       fake.city(),
            "region":     random.choice(REGIONS),
            "segment_id": random.randint(1, len(SEGMENT_NAMES)),
        })

    # ── 5. products ──────────────────────────────────────────
    products = []
    pid = 1
    for cat_name, items in PRODUCTS_BY_CATEGORY.items():
        for prod_name, base_price in items:
            products.append({
                "id":          pid,
                "name":        prod_name,
                "category_id": cat_name_to_id[cat_name],
                "brand_id":    random.randint(1, len(BRANDS)),
                "price":       base_price,
                "sku":         fake.bothify("SKU-####-???").upper(),
            })
            pid += 1

    # ── 6. warehouses ────────────────────────────────────────
    warehouses = [
        {"id": i + 1, "name": f"{region} Warehouse", "city": fake.city(), "region": region}
        for i, region in enumerate(REGIONS)
    ]

    # ── 7. inventory ─────────────────────────────────────────
    inventory = []
    inv_id = 1
    for product in products:
        for warehouse in warehouses:
            inventory.append({
                "id":            inv_id,
                "product_id":    product["id"],
                "warehouse_id":  warehouse["id"],
                "stock_qty":     random.randint(0, 500),
                "reorder_level": random.randint(10, 50),
            })
            inv_id += 1

    # ── 8. departments ───────────────────────────────────────
    departments = [
        {"id": i + 1, "department_name": dept, "manager_id": None}  # updated after employees
        for i, dept in enumerate(DEPTS)
    ]

    # ── 9. stores ────────────────────────────────────────────
    n_stores = 10
    stores = []
    for i in range(n_stores):
        stores.append({
            "id":         i + 1,
            "name":       f"{fake.city()} {random.choice(STORE_TYPES)} Store",
            "city":       fake.city(),
            "region":     random.choice(REGIONS),
            "store_type": random.choice(STORE_TYPES),
        })

    # ── 10. employees ────────────────────────────────────────
    n_employees = 50
    employees = []
    for i in range(n_employees):
        dept_id = random.randint(1, len(DEPTS))
        employees.append({
            "id":            i + 1,
            "name":          fake.name(),
            "role":          random.choice(ROLES),
            "department_id": dept_id,
            "store_id":      random.randint(1, n_stores),
            "salary":        random.randint(20000, 120000),
        })

    # Assign a manager per department (first employee in that dept)
    dept_managers = {}
    for emp in employees:
        did = emp["department_id"]
        if did not in dept_managers:
            dept_managers[did] = emp["id"]
    for dept in departments:
        dept["manager_id"] = dept_managers.get(dept["id"], 1)

    # ── 11. orders ───────────────────────────────────────────
    orders = []
    start_date = datetime(2023, 1, 1)
    for i in range(n_orders):
        orders.append({
            "id":          i + 1,
            "customer_id": random.randint(1, n_customers),
            "order_date":  (start_date + timedelta(days=random.randint(0, 730))).date(),
            "status":      random.choice(ORDER_STATUSES),
            "channel":     random.choice(CHANNELS),
        })

    # ── 12. order_items ──────────────────────────────────────
    order_items = []
    oi_id = 1
    for order in orders:
        n_items = random.randint(1, 5)
        for _ in range(n_items):
            product   = random.choice(products)
            qty       = random.randint(1, 10)
            discount  = round(random.uniform(0, 0.30), 2)
            order_items.append({
                "id":         oi_id,
                "order_id":   order["id"],
                "product_id": product["id"],
                "quantity":   qty,
                "unit_price": product["price"],
                "discount":   discount,
            })
            oi_id += 1

    # ── 13. returns ──────────────────────────────────────────
    returns = []
    ret_id  = 1
    # ~10% of order items get returned
    returnable = [oi for oi in order_items if random.random() < 0.10]
    for oi in returnable:
        order      = next(o for o in orders if o["id"] == oi["order_id"])
        return_date = order["order_date"] + timedelta(days=random.randint(1, 30))
        returns.append({
            "id":            ret_id,
            "order_item_id": oi["id"],
            "return_date":   return_date,
            "reason":        random.choice(RETURN_REASONS),
        })
        ret_id += 1

    # ── 14. payments ─────────────────────────────────────────
    payments = []
    for order in orders:
        items       = [oi for oi in order_items if oi["order_id"] == order["id"]]
        total       = sum(oi["unit_price"] * oi["quantity"] * (1 - oi["discount"]) for oi in items)
        pay_date    = order["order_date"] + timedelta(days=random.randint(0, 3))
        payments.append({
            "id":             order["id"],
            "order_id":       order["id"],
            "payment_date":   pay_date,
            "method":         random.choice(METHODS),
            "amount":         round(total, 2),
            "status":         random.choice(PAYMENT_STATUSES),
        })

    # ── 15. store_sales ──────────────────────────────────────
    n_store_sales = n_orders // 2
    store_sales   = []
    for i in range(n_store_sales):
        product  = random.choice(products)
        qty      = random.randint(1, 20)
        revenue  = round(product["price"] * qty * random.uniform(0.85, 1.0), 2)
        sale_date = (start_date + timedelta(days=random.randint(0, 730))).date()
        store_sales.append({
            "id":         i + 1,
            "store_id":   random.randint(1, n_stores),
            "product_id": product["id"],
            "sale_date":  sale_date,
            "quantity":   qty,
            "revenue":    revenue,
        })

    return {
        "customer_segments": customer_segments,
        "categories":        categories,
        "brands":            brands,
        "customers":         customers,
        "products":          products,
        "warehouses":        warehouses,
        "inventory":         inventory,
        "departments":       departments,
        "stores":            stores,
        "employees":         employees,
        "orders":            orders,
        "order_items":       order_items,
        "returns":           returns,
        "payments":          payments,
        "store_sales":       store_sales,
    }