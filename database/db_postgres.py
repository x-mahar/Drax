# database/db_postgres.py

import psycopg2
import psycopg2.extras
import json
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

def get_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )

def execute_query(sql: str) -> dict:
    """
    Executes a SQL query on PostgreSQL.
    Returns a dict with status, columns, rows, and JSON output.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(sql)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        results = [dict(row) for row in rows]

        return {
            "status": "success",
            "row_count": len(results),
            "data": results
        }

    except psycopg2.Error as e:
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