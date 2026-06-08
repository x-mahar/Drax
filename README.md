# NL to Any DB — AI-Powered Business Intelligence

> Convert plain English questions into the right query language, execute them on any database, and get business-focused answers with structured chart data via a REST API.

---

## What is this?

A completed Proof of Concept (POC) that validates whether an LLM can reliably convert natural language queries into the correct query language (SQL, MongoDB, Redis, ChromaDB), execute them on real databases, and return structured business insights with chart configurations — all via a FastAPI REST endpoint ready for any frontend.

**Powered by:** Groq (LLaMA 3.3 70B) + Python + 6 databases + Schema Pruning + FastAPI

---

## Live API Demo

```bash
# Start the server
python -m uvicorn api.main:app --reload --port 8000

# Ask a question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"show total revenue by product category\"}"
```

```json
{
  "status": "success",
  "question": "show total revenue by product category",
  "db_type": "postgres",
  "sql": "SELECT c.category_name, SUM(s.revenue) AS total_revenue FROM store_sales s JOIN products p ON s.product_id = p.id JOIN categories c ON p.category_id = c.id GROUP BY c.category_name ORDER BY total_revenue DESC",
  "answer": "Electronics dominates revenue at INR 15.8M (76.1% share), followed by Footwear at INR 1.3M.",
  "key_insights": [
    "Total Revenue: INR 20,822,108.99",
    "Number of Categories: 8",
    "Highest: INR 15,843,198.60 (Electronics)",
    "Lowest: INR 119,526.86 (Grocery)"
  ],
  "charts": [
    {
      "type": "horizontal_bar",
      "title": "Revenue by Category",
      "x_key": "category_name",
      "y_key": "total_revenue",
      "x_label": "Category",
      "y_label": "Revenue (INR)"
    },
    {
      "type": "pie",
      "title": "Revenue Share by Category",
      "x_key": "category_name",
      "y_key": "total_revenue",
      "x_label": "Category",
      "y_label": "Share"
    }
  ],
  "data": [...],
  "row_count": 8,
  "self_healed": false,
  "message": null
}
```

---

## Project Structure

```
nl-to-sql-poc/
│
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app — /query, /history, /health endpoints
│   └── models.py            # Pydantic request/response shapes
│
├── data/
│   ├── seed_postgres_retail.py   # Seeds PostgreSQL with full 15-table retail schema
│   ├── seed_mongo_retail.py      # Seeds MongoDB with retail schema
│   ├── seed_mysql_retail.py      # Seeds MySQL with retail schema
│   ├── seed_sqlite_retail.py     # Seeds SQLite with retail schema
│   ├── seed_redis_retail.py      # Seeds Redis with retail schema
│   ├── seed_chroma_retail.py     # Seeds ChromaDB with retail schema
│   └── generate_retail_data.py   # Faker-based retail data generator
│
├── database/
│   ├── db.py                # SQLite connector
│   ├── db_postgres.py       # PostgreSQL connector
│   ├── db_mongo.py          # MongoDB connector
│   ├── db_mysql.py          # MySQL connector
│   ├── db_redis.py          # Redis connector
│   ├── db_chroma.py         # ChromaDB connector
│   └── schema_detector.py   # Auto schema detection (all 6 DBs)
│
├── llm/
│   └── groq_client.py       # All LLM functions:
│                            #   - is_data_question()
│                            #   - generate_sql()
│                            #   - regenerate_sql()      <- self-healing
│                            #   - generate_answer()
│                            #   - generate_chart_data() <- structured JSON for UI
│                            #   - generate_matplotlib() <- CLI fallback
│                            #   - generate_mongo_query()
│                            #   - generate_redis_query()
│                            #   - generate_chroma_query()
│
├── core/
│   ├── validator.py         # SQL safety check (blocks DROP, DELETE etc.)
│   ├── visualizer.py        # Executes matplotlib chart code (CLI)
│   └── schema_router.py     # Cosine similarity schema pruning
│
├── tests/
│   └── benchmark.py         # 25-question stress test across 5 tiers
│
├── charts/                  # Session chart history saved here
├── chroma_db/               # ChromaDB local storage (auto-created)
├── main.py                  # CLI entry point
├── config.py                # All settings + DB_TYPE switch + schema index
├── requirements.txt         # All dependencies
├── .env                     # API keys & credentials (never commit)
└── sales.db                 # SQLite database file
```

---

## How It Works

```
User Input (plain English)
        |
Intent Check              -> blocks gibberish, greetings, typos, off-topic
        |
DB Type Check             -> which DB are we using?
        |
Schema Pruning            -> cosine similarity picks top 5 relevant tables
        |                    (not the full schema — ~95% token reduction)
LLM generates query       -> SQL / MongoDB / Redis / ChromaDB query
        |
SQL Validator             -> blocks dangerous queries (SQL only)
        |
DB Executor               -> runs on the selected database
        |
Self-Healing Layer        -> if error or too few rows -> re-prompt LLM with problem
        |
LLM generates Answer      -> business-focused insights in INR (JSON)
        |
LLM generates Chart Data  -> chart type + x/y keys decided by LLM (JSON)
        |
API Response              -> answer + insights + chart config + raw data
        |
CLI                       -> matplotlib 2x2 dashboard rendered on screen
Session History           -> every query stored, saved on exit
```

---

## Protection Layers

```
Layer 1 — Intent Check      blocks gibberish, typos, greetings, off-topic
Layer 2 — SQL Validator     blocks DROP, DELETE, UPDATE, DDL statements
Layer 3 — DB Executor       catches runtime & syntax errors
Layer 4 — Self-Healing      re-prompts LLM with error context on failure
```

---

## Schema Pruning — How It Works

With enterprise schemas (15+ tables), sending the full schema to the LLM on every query wastes tokens and reduces accuracy.

`schema_router.py` embeds the schema once on startup using `all-MiniLM-L6-v2` and uses cosine similarity to pick only the top 5 relevant tables per query.

```
Full schema (15 tables) -> embed once on startup -> stored in memory
User question           -> embed at query time
Cosine similarity       -> pick top 5 most relevant tables
LLM prompt             -> receives only those 5 tables (~200 tokens)

Token saving: ~95% reduction per query (4000 tokens -> ~200 tokens)
```

---

## Self-Healing Layer

When a query fails or returns suspicious results, the system automatically retries:

```
Trigger 1 — DB error (wrong column, bad join)
  -> sends error message back to LLM
  -> LLM fixes the SQL
  -> re-executes

Trigger 2 — Too few rows (got 1, expected multiple)
  -> sends problem description to LLM
  -> LLM fixes JOINs and GROUP BY
  -> re-executes

Terminal output:
  Warning: Query failed — triggering self-heal...
  OK: Self-healing succeeded. Got 8 rows.
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Main endpoint — takes question, returns full BI response |
| GET | `/history` | Returns this session's query history |
| DELETE | `/history` | Clears session history |
| GET | `/health` | Server + DB status check |
| GET | `/docs` | Swagger UI — test all endpoints in browser |

### POST /query — Request
```json
{ "question": "which brand has the highest selling products" }
```

### POST /query — Response shape
```json
{
  "status": "success",
  "question": "string",
  "db_type": "postgres",
  "sql": "SELECT ...",
  "answer": "string",
  "key_insights": ["string"],
  "charts": [
    {
      "type": "bar | line | pie | scatter | horizontal_bar",
      "title": "string",
      "x_key": "string",
      "y_key": "string",
      "x_label": "string",
      "y_label": "string"
    }
  ],
  "data": [{}],
  "row_count": 8,
  "self_healed": false,
  "message": null
}
```

---

## Supported Databases

| # | DB | Type | Query Language | Status |
|---|-----|------|---------------|--------|
| 1 | SQLite | SQL | SQL | Done |
| 2 | PostgreSQL | SQL | SQL | Done |
| 3 | MySQL | SQL | SQL | Done |
| 4 | MongoDB | NoSQL | JSON query | Done |
| 5 | Redis | NoSQL | Key-Value ops | Done |
| 6 | ChromaDB | VectorDB | Semantic search | Done |

---

## Retail Enterprise Schema (15 Tables)

Full FK-connected retail schema seeded across all 6 DBs using Faker (Indian locale).

| Domain | Tables |
|--------|--------|
| Customer | customers, customer_segments |
| Product | products, categories, brands |
| Sales | orders, order_items, returns |
| Inventory | warehouses, inventory |
| Store | stores, store_sales |
| HR | employees, departments |
| Finance | payments |

---

## Switch Database — One Line

```python
# config.py
DB_TYPE = "sqlite"      # SQLite
DB_TYPE = "postgres"    # PostgreSQL
DB_TYPE = "mysql"       # MySQL
DB_TYPE = "mongo"       # MongoDB
DB_TYPE = "redis"       # Redis
DB_TYPE = "chroma"      # ChromaDB
```

---

## Setup & Installation

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd nl-to-sql-poc
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure `.env`
```bash
GROQ_API_KEY=your_groq_api_key_here

# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=poc_db
PG_USER=postgres
PG_PASSWORD=your_password_here

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=poc_db
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=poc_db
MONGO_COLLECTION=sales

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_PATH=./chroma_db
```

### 5. Seed the database
```bash
# PostgreSQL — recommended
python -m data.seed_postgres_retail

# MySQL
python -m data.seed_mysql_retail

# MongoDB
python -m data.seed_mongo_retail

# SQLite
python -m data.seed_sqlite_retail

# Redis
python -m data.seed_redis_retail

# ChromaDB
python -m data.seed_chroma_retail
```

### 6. Set DB type in `config.py`
```python
DB_TYPE = "postgres"
```

### 7. Run CLI
```bash
python main.py
```

### 8. Run API server
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### 9. Open Swagger UI
```
http://localhost:8000/docs
```

---

## Sample Queries

### Single Table
```
show all products in Electronics category
list all stores in North region
which warehouses are running low on stock
show all employees in Sales department
```

### Multi-Table Joins
```
which customers placed the most orders
show total revenue by product category
top 10 customers by total amount spent
which brand has the highest selling products
show all orders with payment status Failed
```

### Deep Joins (6+ Tables)
```
show total revenue by brand for completed orders only
compare online vs in-store revenue by product category
show top 10 customers by revenue who never returned any item
show revenue growth month over month for 2023 vs 2024
which warehouse region has the lowest stock for top selling products
```

---

## Benchmark / Stress Test

```bash
python -m tests.benchmark
```

Runs 25 questions across 5 tiers, measures response time, tracks self-healing.
Saves results to `tests/benchmark_results.json` and `tests/benchmark_summary.txt`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API — LLaMA 3.3 70B |
| API | FastAPI + Uvicorn |
| Schema Pruning | sentence-transformers (all-MiniLM-L6-v2) + cosine similarity |
| SQL DBs | SQLite, PostgreSQL, MySQL |
| NoSQL DBs | MongoDB, Redis |
| VectorDB | ChromaDB |
| Charts (CLI) | Matplotlib + Seaborn (2x2 dashboard) |
| Charts (API) | Structured JSON — Recharts ready |
| Data Generation | Faker (Indian locale) |
| Language | Python 3.11 |
| Config | python-dotenv |

---

## Current Status

| Feature | Status |
|---|---|
| NL to SQL generation | Done |
| NL to MongoDB query | Done |
| NL to Redis query | Done |
| NL to ChromaDB semantic search | Done |
| SQL Validator | Done |
| SQLite support | Done |
| PostgreSQL support | Done |
| MySQL support | Done |
| MongoDB support | Done |
| Redis support | Done |
| ChromaDB support | Done |
| Business insights (INR) | Done |
| Auto 2x2 chart dashboard (CLI) | Done |
| Structured chart data (API) | Done |
| LLM picks chart type automatically | Done |
| Chart history per session | Done |
| Intent classification (typo-safe) | Done |
| DB swap (one line) | Done |
| Auto schema detection (all 6 DBs) | Done |
| Schema pruning (cosine similarity) | Done |
| Self-healing layer | Done |
| Enterprise retail schema (15 tables) | Done |
| Faker-based data generator | Done |
| Seeded all 6 DBs | Done |
| FastAPI REST endpoint | Done |
| Session history API | Done |
| Benchmark / stress test | Done |
| Virtual environment setup | Done |

---

## Roadmap

### Next — Backend Optimizations
- [ ] Parallel LLM calls (answer + chart in parallel — saves 1-2s per query)
- [ ] Schema cache persistence (survive server restarts)
- [ ] Response caching (same question = instant response)
- [ ] DB connection pooling (PostgreSQL at scale)

### Phase 5 — Product Features
- [ ] Web UI (React + Recharts — API already ready)
- [ ] Query history persistence (database-backed)
- [ ] Multi-schema support
- [ ] Company-specific DB connector (plug-in architecture)
- [ ] Authentication & API key management

### Phase 6 — Enterprise DBs
- [ ] Snowflake (cloud data warehouse)
- [ ] Delta Lake (big data + Spark)
- [ ] Elasticsearch (search & analytics)

---

## Long Term Vision

> Any company plugs in their DB, employees ask questions in plain English, and get instant business insights and charts. No SQL knowledge required.

This POC builds what Power BI charges as a premium feature ("Q&A Visual") — from scratch, for free, with open-source LLMs — across 6 database types with enterprise-grade schema pruning, self-healing queries, and a production-ready REST API.

---

## Get Your Free Groq API Key

https://console.groq.com