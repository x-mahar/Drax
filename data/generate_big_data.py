# data/generate_big_data.py

import random
from faker import Faker

fake = Faker("en_IN")  # Indian locale for realistic names

# Fixed options
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard"]

# Generate 200 unique customer names — they'll repeat across 10k rows
# This gives us realistic repeat customer patterns
CUSTOMERS = list(set([fake.name() for _ in range(200)]))

def generate_big_data(num_rows: int = 10000) -> list:
    """
    Generates num_rows of realistic sales data.
    Returns a list of dicts.
    """
    data = []

    for _ in range(num_rows):
        row = {
            "date": fake.date_between(
                start_date="-3y",   # 3 years back
                end_date="today"
            ).strftime("%Y-%m-%d"),
            "region":        random.choice(REGIONS),
            "product":       random.choice(PRODUCTS),
            "revenue":       round(random.uniform(100, 5000), 2),
            "customer_name": random.choice(CUSTOMERS),
        }
        data.append(row)

    return data


if __name__ == "__main__":
    data = generate_big_data()
    print(f"✅ Generated {len(data)} rows")
    print(f"Sample row: {data[0]}")
    print(f"Sample row: {data[1]}")
    print(f"Sample row: {data[2]}")