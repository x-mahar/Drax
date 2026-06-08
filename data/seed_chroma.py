# data/seed_chroma.py

import chromadb
from config import CHROMA_PATH
from data.generate_big_data import generate_big_data

def seed():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection if exists
    try:
        client.delete_collection("sales")
    except:
        pass

    # Create collection
    collection = client.get_or_create_collection(
        name="sales",
        metadata={"hnsw:space": "cosine"}
    )

    # Generate 10k rows
    data = generate_big_data(500)

    # Add id to each row
    for i, row in enumerate(data):
        row["id"] = str(i + 1)

    # Build natural language documents
    documents = [
        f"Sale in {d['region']} region. Product: {d['product']}. Revenue: {d['revenue']}. Customer: {d['customer_name']}. Date: {d['date']}."
        for d in data
    ]

    ids = [d["id"] for d in data]
    metadatas = [{k: v for k, v in d.items() if k != "id"} for d in data]

    # ChromaDB has batch limit — insert in chunks of 1000
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        collection.add(
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
            ids=ids[i:i + batch_size]
        )
        print(f"  Inserted batch {i // batch_size + 1}/10...")

    print(f"✅ ChromaDB seeded with {len(data)} records!")

if __name__ == "__main__":
    seed()