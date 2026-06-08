# database/db_chroma.py

import json
import chromadb
from config import CHROMA_PATH

CHROMA_COLLECTION = "sales"


def get_connection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    return client, collection


def execute_query(query: dict) -> dict:
    """
    Executes a ChromaDB query on the sales collection.
    Accepts a dict with 'operation' and 'params'.

    Supported operations:
      - semantic_search : natural language similarity search
      - get_all         : fetch all records (with optional limit)
      - get_by_id       : fetch one or more records by ID

    Returns a dict with status, row_count, and data.
    """
    try:
        _, collection = get_connection()

        operation = query.get("operation", "semantic_search")
        params = query.get("params", {})

        # ── 1. Semantic / natural-language search ─────────────────────────────
        if operation == "semantic_search":
            query_text = params.get("query_text", "")
            n_results  = params.get("n_results", 5)
            where      = params.get("where", None)          # optional metadata filter

            if not query_text:
                return {
                    "status": "error",
                    "message": "semantic_search requires 'query_text' in params",
                    "data": []
                }

            kwargs = {
                "query_texts": [query_text],
                "n_results":   n_results,
                "include":     ["documents", "metadatas", "distances"]
            }
            if where:
                kwargs["where"] = where

            raw = collection.query(**kwargs)

            # Flatten ChromaDB's nested-list response into a clean list of dicts
            results = []
            for i, doc in enumerate(raw["documents"][0]):
                results.append({
                    **raw["metadatas"][0][i],
                    "document":         doc,
                    "similarity_score": round(1 - raw["distances"][0][i], 4)
                })

        # ── 2. Get all records ─────────────────────────────────────────────────
        elif operation == "get_all":
            limit = params.get("limit", None)

            raw = collection.get(include=["documents", "metadatas"])

            results = []
            for i, doc in enumerate(raw["documents"]):
                results.append({
                    "id":       raw["ids"][i],
                    **raw["metadatas"][i],
                    "document": doc
                })

            if limit:
                results = results[:limit]

        # ── 3. Get by ID(s) ────────────────────────────────────────────────────
        elif operation == "get_by_id":
            ids = params.get("ids", [])

            if not ids:
                return {
                    "status": "error",
                    "message": "get_by_id requires 'ids' list in params",
                    "data": []
                }

            raw = collection.get(ids=ids, include=["documents", "metadatas"])

            results = []
            for i, doc in enumerate(raw["documents"]):
                results.append({
                    "id":       raw["ids"][i],
                    **raw["metadatas"][i],
                    "document": doc
                })

        else:
            return {
                "status": "error",
                "message": f"Unsupported operation: {operation}",
                "data": []
            }

        return {
            "status":    "success",
            "row_count": len(results),
            "data":      results
        }

    except Exception as e:
        return {
            "status":  "error",
            "message": str(e),
            "data":    []
        }


def print_results(result: dict):
    if result["status"] == "error":
        print(f"\n❌ Query Error: {result['message']}")
        return

    print(f"\n✅ {result['row_count']} row(s) returned\n")
    print(json.dumps(result["data"], indent=2, default=str))