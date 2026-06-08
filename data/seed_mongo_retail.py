# data/seed_mongo_retail.py
# creates all 15 collections + seeds them

from pymongo import MongoClient
from datetime import date, datetime
from config import MONGO_URI, MONGO_DATABASE
from data.generate_retail_data import generate_retail_data


def convert_dates(records: list[dict]) -> list[dict]:
    """Convert datetime.date → datetime.datetime so MongoDB (BSON) can encode them."""
    converted = []
    for record in records:
        converted.append({
            k: datetime(v.year, v.month, v.day) if isinstance(v, date) else v
            for k, v in record.items()
        })
    return converted


def seed(n_orders: int = 1000):
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]

    # ── DROP existing retail collections (clean slate) ────────
    for collection in [
        "store_sales", "payments", "returns", "order_items", "orders",
        "employees", "stores", "departments", "inventory", "warehouses",
        "products", "customers", "brands", "categories", "customer_segments"
    ]:
        db[collection].drop()
    print("🗑️  Dropped existing retail collections.")

    # ── GENERATE data ─────────────────────────────────────────
    print(f"⏳ Generating retail data ({n_orders} orders)...")
    data = generate_retail_data(n_orders)

    # ── INSERT — parent collections first ─────────────────────
    # Note: convert_dates() applied to collections with date fields
    #       (orders, returns, payments, store_sales)

    db["customer_segments"].insert_many(data["customer_segments"])
    db["categories"].insert_many(data["categories"])
    db["brands"].insert_many(data["brands"])
    db["customers"].insert_many(data["customers"])
    db["products"].insert_many(data["products"])
    db["warehouses"].insert_many(data["warehouses"])
    db["inventory"].insert_many(data["inventory"])
    db["departments"].insert_many(data["departments"])
    db["stores"].insert_many(data["stores"])
    db["employees"].insert_many(data["employees"])
    db["orders"].insert_many(convert_dates(data["orders"]))
    db["order_items"].insert_many(data["order_items"])
    db["returns"].insert_many(convert_dates(data["returns"]))
    db["payments"].insert_many(convert_dates(data["payments"]))
    db["store_sales"].insert_many(convert_dates(data["store_sales"]))

    client.close()

    # ── Summary ───────────────────────────────────────────────
    print("\n✅ MongoDB retail schema seeded successfully!")
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