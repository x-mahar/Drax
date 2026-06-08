# data/seed_mongo.py

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION
from data.generate_big_data import generate_big_data

def seed():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    collection = db[MONGO_COLLECTION]

    # Clear existing data
    collection.delete_many({})

    # Generate & insert 10k rows
    data = generate_big_data(10000)
    collection.insert_many(data)

    client.close()
    print(f"✅ MongoDB seeded with {len(data)} rows!")

if __name__ == "__main__":
    seed()