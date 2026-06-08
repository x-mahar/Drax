# database/db_mysql.py

import mysql.connector
import json
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD

def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )

def execute_query(sql: str) -> dict:
    """
    Executes a SQL query on MySQL.
    Returns a dict with status, columns, rows, and JSON output.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

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

    except mysql.connector.Error as e:
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