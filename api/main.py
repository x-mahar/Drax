# api/main.py

import sys
import os
import time
import hashlib
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import QueryRequest, QueryResponse, ChartConfig
from config import DB_TYPE
from core.validator import validate_sql
from llm.groq_client import (
    is_data_question,
    generate_sql,
    regenerate_sql,
    generate_answer,
    generate_chart_data,
    generate_mongo_query,
    generate_redis_query,
    generate_chroma_query,
)

if DB_TYPE == "sqlite":
    from database.db import execute_query
elif DB_TYPE == "postgres":
    from database.db_postgres import execute_query
elif DB_TYPE == "mysql":
    from database.db_mysql import execute_query
elif DB_TYPE == "mongo":
    from database.db_mongo import execute_query
elif DB_TYPE == "redis":
    from database.db_redis import execute_query
elif DB_TYPE == "chroma":
    from database.db_chroma import execute_query

app = FastAPI(title="NL to Any DB — BI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Persistent disk cache (1 hour TTL) ───────────────────────
CACHE_TTL  = 3600
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "query_cache.json")

def _load_cache() -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[cache] Load error: {e}")
    return {}

class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        import decimal, datetime
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, cls=_DecimalEncoder)
    except Exception as e:
        print(f"[cache] Save error: {e}")

_query_cache: dict = _load_cache()
print(f"[cache] Loaded {len(_query_cache)} cached entries from disk.")

def _cache_key(question: str) -> str:
    return hashlib.md5(question.strip().lower().encode()).hexdigest()

def _get_cache(question: str):
    key = _cache_key(question)
    if key in _query_cache:
        entry = _query_cache[key]
        if time.time() - entry["ts"] < CACHE_TTL:
            print(f"[cache] HIT: {question[:60]}")
            return entry["data"]
        else:
            del _query_cache[key]
    return None

def _set_cache(question: str, data: dict):
    key = _cache_key(question)
    _query_cache[key] = {"ts": time.time(), "data": data}
    _save_cache(_query_cache)
    print(f"[cache] SET: {question[:60]} ({len(_query_cache)} entries)")

# ── Session history ───────────────────────────────────────────
_session_history: list[dict] = []

# ── Auto warm-up queries (matches config.js) ─────────────────
WARMUP_QUESTIONS = [
    "show total revenue by product category",
    "top 5 customers by order count",
    "top 10 products by revenue",
    "total payments received by month",
    "show total orders by customer segment",
    # duplicates are fine — cache deduplicates by question hash
]

SINGLE_ROW_KEYWORDS = ["total", "average", "how many", "count", "sum", "overall"]

def _expects_multiple_rows(question: str) -> bool:
    return not any(kw in question.lower() for kw in SINGLE_ROW_KEYWORDS)


@app.on_event("startup")
async def warmup_cache():
    """Auto-populate cache on startup for questions not already cached."""
    import asyncio
    uncached = [q for q in WARMUP_QUESTIONS if _get_cache(q) is None]
    if not uncached:
        print(f"[cache] All {len(WARMUP_QUESTIONS)} warmup queries already cached.")
        return
    print(f"[cache] Warming up {len(uncached)} uncached queries in background...")

    async def _warm(question: str, delay: float):
        await asyncio.sleep(delay)
        try:
            from api.models import QueryRequest
            req = QueryRequest(question=question)
            await query(req)
            print(f"[cache] Warmed: {question[:60]}")
        except Exception as e:
            print(f"[cache] Warm error for '{question[:40]}': {e}")

    for i, q in enumerate(uncached):
        asyncio.create_task(_warm(q, delay=i * 4.0))  # 4s apart to avoid rate limits


@app.get("/health")
def health():
    return {"status": "ok", "db_type": DB_TYPE, "cache_entries": len(_query_cache), "history_count": len(_session_history)}

@app.get("/history")
def get_history():
    return {"count": len(_session_history), "history": _session_history}

@app.delete("/history")
def clear_history():
    _session_history.clear()
    return {"status": "cleared"}

@app.delete("/cache")
def clear_cache():
    _query_cache.clear()
    _save_cache(_query_cache)
    return {"status": "cache cleared"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # ── Cache check ───────────────────────────────────────────
    cached = _get_cache(question)
    if cached:
        return QueryResponse(**{**cached, "charts": [ChartConfig(**c) for c in cached.get("charts", [])]})

    # ── Intent check ─────────────────────────────────────────
    if not is_data_question(question):
        raise HTTPException(status_code=422, detail="That doesn't look like a data question. Try asking about revenue, products, customers, or orders.")

    self_healed = False
    query_context = None
    result = None

    if DB_TYPE == "chroma":
        r = generate_chroma_query(question)
        if r["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {r['message']}")
        query_context = r["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    elif DB_TYPE == "mongo":
        r = generate_mongo_query(question)
        if r["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {r['message']}")
        query_context = r["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    elif DB_TYPE == "redis":
        r = generate_redis_query(question)
        if r["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {r['message']}")
        query_context = r["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    else:
        llm_response = generate_sql(question)
        if llm_response["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {llm_response['message']}")

        sql = llm_response["sql"]
        validation = validate_sql(sql)
        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=f"Unsafe query blocked: {validation['message']}")

        result = execute_query(sql)

        if result["status"] == "error":
            fix = regenerate_sql(question, bad_sql=sql, problem=f"DB error: {result['message']}")
            if fix["status"] == "success":
                sql = fix["sql"]
                if validate_sql(sql)["is_valid"]:
                    result = execute_query(sql)
                    if result["status"] == "success":
                        self_healed = True
            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

        elif result["row_count"] <= 1 and _expects_multiple_rows(question):
            fix = regenerate_sql(question, bad_sql=sql, problem=f"Only {result['row_count']} row(s). Fix JOINs/GROUP BY.")
            if fix["status"] == "success":
                sql = fix["sql"]
                if validate_sql(sql)["is_valid"]:
                    retry = execute_query(sql)
                    if retry["status"] == "success" and retry["row_count"] > result["row_count"]:
                        result = retry
                        self_healed = True

        query_context = sql

    interpretation = generate_answer(question, query_context, result["data"])
    chart_response  = generate_chart_data(question, query_context, result["data"])

    answer = interpretation.get("answer", "") if interpretation["status"] == "success" else ""
    key_insights = interpretation.get("key_insights", []) if interpretation["status"] == "success" else []
    charts_raw = chart_response.get("charts", []) if chart_response["status"] == "success" else []
    charts = [ChartConfig(**c) for c in charts_raw]

    response_data = dict(
        status="success",
        question=question,
        db_type=DB_TYPE,
        sql=str(query_context) if DB_TYPE in ("sqlite", "postgres", "mysql") else None,
        answer=answer,
        key_insights=key_insights,
        charts=charts_raw,
        data=result["data"],
        row_count=result["row_count"],
        self_healed=self_healed,
        message=None,
    )

    _set_cache(question, response_data)

    _session_history.append({
        "timestamp":    datetime.utcnow().isoformat() + "Z",
        "question":     question,
        "db_type":      DB_TYPE,
        "sql":          response_data["sql"],
        "answer":       answer,
        "key_insights": key_insights,
        "charts":       charts_raw,
        "row_count":    result["row_count"],
        "self_healed":  self_healed,
    })

    return QueryResponse(**{**response_data, "charts": charts})