# database/db.py

import sqlite3
import json
from config import DB_PATH

def execute_query(sql: str) -> dict:
    """
    Executes a SQL query on the SQLite database.
    Returns a dict with status, columns, rows, and JSON output.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # lets us access columns by name
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        # Convert rows to list of dicts
        results = [dict(row) for row in rows]

        return {
            "status": "success",
            "row_count": len(results),
            "data": results
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e),
            "data": []
        }


def print_results(result: dict):
    """
    Pretty prints the query result in the CLI.
    """
    if result["status"] == "error":
        print(f"\n❌ Query Error: {result['message']}")
        return

    print(f"\n✅ {result['row_count']} row(s) returned\n")
    print(json.dumps(result["data"], indent=2))