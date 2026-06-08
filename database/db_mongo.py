# database/db_mongo.py

import json
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION

def get_connection():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    return client, db[MONGO_COLLECTION]

def execute_query(query: dict) -> dict:
    """
    Executes a MongoDB query on the sales collection.
    Accepts a dict with 'operation' and 'params'.
    Returns a dict with status, row_count, and data.
    """
    try:
        client, collection = get_connection()

        operation = query.get("operation", "find")
        params = query.get("params", {})

        if operation == "find":
            filter_ = params.get("filter", {})
            projection = params.get("projection", {"_id": 0})
            limit = params.get("limit", 0)
            cursor = collection.find(filter_, projection)
            if limit:
                cursor = cursor.limit(limit)
            results = list(cursor)

        elif operation == "aggregate":
            pipeline = params.get("pipeline", [])
            results = list(collection.aggregate(pipeline))
            # remove _id from results
            for r in results:
                r.pop("_id", None)

        else:
            return {
                "status": "error",
                "message": f"Unsupported operation: {operation}",
                "data": []
            }

        client.close()

        return {
            "status": "success",
            "row_count": len(results),
            "data": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": []
        }


def print_results(result: dict):
    if result["status"] == "error":
        print(f"\n❌ Query Error: {result['message']}")
        return

    print(f"\n✅ {result['row_count']} row(s) returned\n")
    print(json.dumps(result["data"], indent=2, default=str))