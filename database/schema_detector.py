# database/schema_detector.py

"""
Auto Schema Detector
Reads the live schema from whichever DB is active
and returns a formatted string for LLM prompt injection.
No more hardcoded DB_SCHEMA in config.py.
"""
# import config

def detect_schema(db_type: str, **kwargs) -> str:
    """
    Main entry point.
    Call with db_type + connection params.
    Returns a human-readable schema string for LLM prompts.
    """
    detectors = {
        "sqlite":   _detect_sqlite,
        "postgres": _detect_postgres,
        "mysql":    _detect_mysql,
        "mongo":    _detect_mongo,
        "redis":    _detect_redis,
        "chroma":   _detect_chroma,
    }

    detector = detectors.get(db_type)
    if not detector:
        return f"Unknown DB type: {db_type}"

    try:
        return detector(**kwargs)
    except Exception as e:
        return f"Schema detection failed for {db_type}: {str(e)}"


# ─────────────────────────────────────────────
# SQLite
# ─────────────────────────────────────────────
def _detect_sqlite(db_path: str = "sales.db", **kwargs) -> str:
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    schema_parts = [f"Database Type: SQLite | File: {db_path}\n"]

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        row_count = cursor.fetchone()[0]

        schema_parts.append(f"Table: {table} ({row_count} rows)")
        for col in columns:
            # col = (cid, name, type, notnull, default, pk)
            pk_marker    = " [PK]"       if col[5] else ""
            null_marker  = " NOT NULL"   if col[3] else ""
            schema_parts.append(f"  - {col[1]} ({col[2]}{null_marker}{pk_marker})")

        # 2 sample rows so LLM understands real values
        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        samples = cursor.fetchall()
        if samples:
            col_names = [col[1] for col in columns]
            schema_parts.append("  Sample rows:")
            for row in samples:
                schema_parts.append(f"    {dict(zip(col_names, row))}")

        schema_parts.append("")  # blank line between tables

    conn.close()
    return "\n".join(schema_parts)


# ─────────────────────────────────────────────
# PostgreSQL
# ─────────────────────────────────────────────
def _detect_postgres(host="localhost", port="5432", database="poc_db",
                     user="postgres", password="", **kwargs) -> str:
    import psycopg2

    conn = psycopg2.connect(
        host=host, port=port, dbname=database, user=user, password=password
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]

    schema_parts = [f"Database Type: PostgreSQL | Database: {database}\n"]

    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (table,))
        columns = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        row_count = cursor.fetchone()[0]

        schema_parts.append(f"Table: {table} ({row_count} rows)")
        for col in columns:
            null_marker = "" if col[2] == "YES" else " NOT NULL"
            schema_parts.append(f"  - {col[0]} ({col[1]}{null_marker})")

        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        samples = cursor.fetchall()
        if samples:
            col_names = [col[0] for col in columns]
            schema_parts.append("  Sample rows:")
            for row in samples:
                schema_parts.append(f"    {dict(zip(col_names, row))}")

        schema_parts.append("")

    conn.close()
    return "\n".join(schema_parts)


# ─────────────────────────────────────────────
# MySQL
# ─────────────────────────────────────────────
def _detect_mysql(host="localhost", port=3306, database="poc_db",
                  user="root", password="", **kwargs) -> str:
    import mysql.connector

    conn = mysql.connector.connect(
        host=host, port=port, database=database, user=user, password=password
    )
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in cursor.fetchall()]

    schema_parts = [f"Database Type: MySQL | Database: {database}\n"]

    for table in tables:
        cursor.execute(f"DESCRIBE {table};")
        columns = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        row_count = cursor.fetchone()[0]

        schema_parts.append(f"Table: {table} ({row_count} rows)")
        for col in columns:
            # col = (Field, Type, Null, Key, Default, Extra)
            pk_marker   = " [PK]"     if col[3] == "PRI" else ""
            null_marker = " NOT NULL" if col[2] == "NO"  else ""
            schema_parts.append(f"  - {col[0]} ({col[1]}{null_marker}{pk_marker})")

        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        samples = cursor.fetchall()
        if samples:
            col_names = [col[0] for col in columns]
            schema_parts.append("  Sample rows:")
            for row in samples:
                schema_parts.append(f"    {dict(zip(col_names, row))}")

        schema_parts.append("")

    conn.close()
    return "\n".join(schema_parts)


# ─────────────────────────────────────────────
# MongoDB
# ─────────────────────────────────────────────
def _detect_mongo(uri="mongodb://localhost:27017", database="poc_db",
                  collection="sales", **kwargs) -> str:
    from pymongo import MongoClient

    client = MongoClient(uri)
    db = client[database]

    collections = db.list_collection_names()
    schema_parts = [f"Database Type: MongoDB | Database: {database}\n"]

    for col_name in collections:
        col = db[col_name]
        row_count = col.count_documents({})

        # Sample 5 docs to infer all possible fields + types
        samples = list(col.find({}, {"_id": 0}).limit(5))

        # Collect all unique fields across samples
        all_fields = {}
        for doc in samples:
            for field, value in doc.items():
                if field not in all_fields:
                    all_fields[field] = type(value).__name__

        schema_parts.append(f"Collection: {col_name} ({row_count} documents)")
        for field, ftype in all_fields.items():
            schema_parts.append(f"  - {field} ({ftype})")

        if samples:
            schema_parts.append("  Sample documents:")
            for doc in samples[:2]:
                schema_parts.append(f"    {doc}")

        schema_parts.append("")

    client.close()
    return "\n".join(schema_parts)


# ─────────────────────────────────────────────
# Redis
# ─────────────────────────────────────────────
def _detect_redis(host="localhost", port=6379, **kwargs) -> str:
    import redis
    import json

    r = redis.Redis(host=host, port=port, decode_responses=True)

    # Scan all keys (safe — uses SCAN not KEYS)
    all_keys = []
    cursor_val = 0
    while True:
        cursor_val, keys = r.scan(cursor_val, count=100)
        all_keys.extend(keys)
        if cursor_val == 0:
            break

    schema_parts = [f"Database Type: Redis | Host: {host}:{port}\n"]
    schema_parts.append(f"Total keys found: {len(all_keys)}\n")

    # Group keys by prefix (e.g. "sale:1" → prefix "sale")
    prefixes = {}
    for key in all_keys:
        prefix = key.split(":")[0] if ":" in key else key
        prefixes.setdefault(prefix, []).append(key)

    for prefix, keys in prefixes.items():
        schema_parts.append(f"Key pattern: {prefix}:* ({len(keys)} keys)")

        # Read one sample key to infer fields
        # Skip non-string keys
        if r.type(keys[0]) != "string":
            schema_parts.append(f"  (non-string key, skipping sample)")
            schema_parts.append("")
            continue
        sample_raw = r.get(keys[0])
        if sample_raw:
            try:
                sample = json.loads(sample_raw)
                schema_parts.append("  Fields (inferred from sample):")
                for field, value in sample.items():
                    schema_parts.append(f"  - {field} ({type(value).__name__})")
                schema_parts.append(f"  Sample: {sample}")
            except Exception:
                schema_parts.append(f"  Raw value: {sample_raw}")

        schema_parts.append("")

    # Check for sorted sets
    sorted_sets = [k for k in all_keys if r.type(k) == "zset"]
    if sorted_sets:
        schema_parts.append("Sorted Sets:")
        for zkey in sorted_sets:
            count = r.zcard(zkey)
            schema_parts.append(f"  - {zkey} ({count} members, ranked by score)")
        schema_parts.append("")

    return "\n".join(schema_parts)


# ─────────────────────────────────────────────
# ChromaDB
# ─────────────────────────────────────────────
def _detect_chroma(chroma_path: str = "./chroma_db", **kwargs) -> str:
    import chromadb

    client = chromadb.PersistentClient(path=chroma_path)
    collections = client.list_collections()

    schema_parts = [f"Database Type: ChromaDB | Path: {chroma_path}\n"]

    for col in collections:
        collection = client.get_collection(col.name)
        count = collection.count()

        schema_parts.append(f"Collection: {col.name} ({count} documents)")

        # Peek at a few records to infer metadata fields
        if count > 0:
            peek = collection.peek(limit=3)

            # Infer metadata fields from first record
            if peek["metadatas"] and peek["metadatas"][0]:
                schema_parts.append("  Metadata fields:")
                for field, value in peek["metadatas"][0].items():
                    schema_parts.append(f"  - {field} ({type(value).__name__})")

            # Show sample documents
            if peek["documents"]:
                schema_parts.append("  Sample documents:")
                for doc in peek["documents"][:2]:
                    schema_parts.append(f"    \"{doc}\"")

        schema_parts.append("")

    return "\n".join(schema_parts)


if __name__ == "__main__":
    from config import DB_TYPE, DB_PATH, CHROMA_PATH
    schema = detect_schema(DB_TYPE, db_path=DB_PATH, chroma_path=CHROMA_PATH)
    print(schema)