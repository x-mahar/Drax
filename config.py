# config.py

import os
from dotenv import load_dotenv
from core.schema_router import build_index


load_dotenv()

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Database — switch to activate a different DB
# DB_TYPE = "sqlite"
DB_TYPE = "postgres"
# DB_TYPE = "mongo"
# DB_TYPE = "mysql"
# DB_TYPE = "redis"
# DB_TYPE = "chroma"

# SQLite
DB_PATH = "sales.db"

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "poc_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "sales")

# PostgreSQL
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "poc_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "poc_db")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ChromaDB
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

# ── Auto Schema Detection ──────────────────────────────────────
# Replaces the old hardcoded DB_SCHEMA string.
# Reads live schema from whichever DB is active.

from database.schema_detector import detect_schema

DB_SCHEMA = detect_schema(
    DB_TYPE,
    # SQLite
    db_path=DB_PATH,
    # Postgres
    host=PG_HOST, port=PG_PORT, database=PG_DATABASE,
    user=PG_USER, password=PG_PASSWORD,
    # MySQL
    # (reuses host/port/database/user/password above)
    # MongoDB
    uri=MONGO_URI, collection=MONGO_COLLECTION,
    # ChromaDB
    chroma_path=CHROMA_PATH,
    # Redis
    # (reuses host/port above)
)

build_index(DB_SCHEMA)

print(f"Schema loaded for {DB_TYPE.upper()}")