# core/validator.py

# Dangerous keywords we never want to execute
DANGEROUS_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT",
    "ALTER", "TRUNCATE", "REPLACE", "CREATE"
]

def validate_sql(sql: str) -> dict:
    """
    Validates SQL query before execution.
    Only allows SELECT statements for this POC.
    Returns dict with is_valid flag and message.
    """

    if not sql or not sql.strip():
        return {
            "is_valid": False,
            "message": "❌ Empty SQL query received."
        }

    sql_upper = sql.upper().strip()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return {
            "is_valid": False,
            "message": "❌ Only SELECT queries are allowed in this POC."
        }

    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in sql_upper:
            return {
                "is_valid": False,
                "message": f"❌ Dangerous keyword detected: '{keyword}'. Query blocked."
            }

    return {
        "is_valid": True,
        "message": "✅ SQL looks safe."
    }