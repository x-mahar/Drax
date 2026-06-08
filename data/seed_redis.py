# data/seed_redis.py

import redis
import json
from config import REDIS_HOST, REDIS_PORT
from data.generate_big_data import generate_big_data

def seed():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Clear existing data
    r.flushdb()

    # Generate 10k rows
    data = generate_big_data(10000)

    # Use pipeline for faster bulk insert
    pipe = r.pipeline()

    for i, sale in enumerate(data, start=1):
        sale["id"] = i
        pipe.set(f"sale:{i}", json.dumps(sale))
        pipe.zadd("sales:by_revenue", {str(i): sale["revenue"]})

    pipe.execute()

    print(f"✅ Redis seeded with {len(data)} rows!")

if __name__ == "__main__":
    seed()