# database/db_redis.py

import redis
import json
from config import REDIS_HOST, REDIS_PORT

def get_connection():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def execute_query(query: dict) -> dict:
    """
    Executes a Redis query.
    Supports operations: get_all, filter_by, top_by_revenue
    """
    try:
        r = get_connection()
        operation = query.get("operation")
        params = query.get("params", {})
        results = []

        if operation == "get_all":
            # Get all sales keys
            keys = r.keys("sale:*")
            for key in sorted(keys):
                data = json.loads(r.get(key))
                results.append(data)

        elif operation == "filter_by":
            # Filter by any field value e.g. region=North
            field = params.get("field")
            value = params.get("value")
            keys = r.keys("sale:*")
            for key in sorted(keys):
                data = json.loads(r.get(key))
                if str(data.get(field, "")).lower() == str(value).lower():
                    results.append(data)

        elif operation == "top_by_revenue":
            # Get top N sales by revenue using sorted set
            limit = params.get("limit", 5)
            # Get top ids by revenue (descending)
            top_ids = r.zrevrange("sales:by_revenue", 0, limit - 1)
            for sale_id in top_ids:
                data = json.loads(r.get(f"sale:{sale_id}"))
                results.append(data)

        elif operation == "group_by":
            # Group by a field and sum revenue
            field = params.get("field")
            keys = r.keys("sale:*")
            groups = {}
            for key in sorted(keys):
                data = json.loads(r.get(key))
                group_key = data.get(field, "unknown")
                if group_key not in groups:
                    groups[group_key] = {"total_revenue": 0, "count": 0}
                groups[group_key]["total_revenue"] += data.get("revenue", 0)
                groups[group_key]["count"] += 1

            for group_key, values in groups.items():
                results.append({field: group_key, **values})

        else:
            return {
                "status": "error",
                "message": f"Unsupported operation: {operation}",
                "data": []
            }

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