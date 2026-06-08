# api/main.py
#
# FastAPI layer — wraps the existing pipeline as a single /query endpoint.
# DB type is controlled by config.py exactly like the CLI.
#
# Run with:
#   uvicorn api.main:app --reload --port 8000
#
# Endpoint:
#   POST /query        { "question": "show revenue by category" }
#   GET  /health       server + DB status check
#   GET  /history      returns this session's query history
#   DELETE /history    clears session history

import sys
import os
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

# ── Auto pick the right DB executor ──────────────────────────
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

# ── App setup ─────────────────────────────────────────────────
app = FastAPI(
    title="NL to Any DB — BI API",
    description="Convert plain English questions into DB queries and get structured BI insights.",
    version="1.0.0",
)

# Allow React dev server (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session history ─────────────────────────────────
# Cleared on server restart — persistent history comes in Phase 5
_session_history: list[dict] = []

SINGLE_ROW_KEYWORDS = ["total", "average", "how many", "count", "sum", "overall"]


def _expects_multiple_rows(question: str) -> bool:
    return not any(kw in question.lower() for kw in SINGLE_ROW_KEYWORDS)


# ── Routes ────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "db_type": DB_TYPE,
        "history_count": len(_session_history),
    }


@app.get("/history")
def get_history():
    return {
        "count": len(_session_history),
        "history": _session_history,
    }


@app.delete("/history")
def clear_history():
    _session_history.clear()
    return {"status": "cleared"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # ── Step 1: Intent check ──────────────────────────────────
    if not is_data_question(question):
        raise HTTPException(
            status_code=422,
            detail="That doesn't look like a data question. Try asking about revenue, products, customers, or orders."
        )

    self_healed = False
    query_context = None
    result = None

    # ── Step 2: Generate query per DB type ───────────────────

    if DB_TYPE == "chroma":
        chroma_response = generate_chroma_query(question)
        if chroma_response["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {chroma_response['message']}")
        query_context = chroma_response["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    elif DB_TYPE == "mongo":
        mongo_response = generate_mongo_query(question)
        if mongo_response["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {mongo_response['message']}")
        query_context = mongo_response["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    elif DB_TYPE == "redis":
        redis_response = generate_redis_query(question)
        if redis_response["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {redis_response['message']}")
        query_context = redis_response["query"]
        result = execute_query(query_context)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

    else:
        # SQL DBs — sqlite / postgres / mysql
        llm_response = generate_sql(question)
        if llm_response["status"] == "error":
            raise HTTPException(status_code=500, detail=f"LLM Error: {llm_response['message']}")

        sql = llm_response["sql"]

        validation = validate_sql(sql)
        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=f"Unsafe query blocked: {validation['message']}")

        result = execute_query(sql)

        # ── Self-healing layer ────────────────────────────────
        if result["status"] == "error":
            fix = regenerate_sql(question, bad_sql=sql,
                                 problem=f"DB execution error: {result['message']}")
            if fix["status"] == "success":
                sql = fix["sql"]
                validation = validate_sql(sql)
                if validation["is_valid"]:
                    result = execute_query(sql)
                    if result["status"] == "success":
                        self_healed = True

            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=f"Query Error: {result['message']}")

        elif result["row_count"] <= 1 and _expects_multiple_rows(question):
            fix = regenerate_sql(
                question, bad_sql=sql,
                problem=(
                    f"Returned only {result['row_count']} row(s). "
                    f"Expected multiple. Fix JOINs and GROUP BY."
                )
            )
            if fix["status"] == "success":
                sql = fix["sql"]
                validation = validate_sql(sql)
                if validation["is_valid"]:
                    retry = execute_query(sql)
                    if retry["status"] == "success" and retry["row_count"] > result["row_count"]:
                        result = retry
                        self_healed = True

        query_context = sql

    # ── Step 3: Generate answer + chart data ─────────────────
    interpretation = generate_answer(question, query_context, result["data"])
    chart_response = generate_chart_data(question, query_context, result["data"])

    answer = ""
    key_insights = []
    if interpretation["status"] == "success":
        answer = interpretation.get("answer", "")
        key_insights = interpretation.get("key_insights", [])

    charts = []
    if chart_response["status"] == "success":
        charts = [
            ChartConfig(**c) for c in chart_response.get("charts", [])
        ]

    # ── Step 4: Build response ────────────────────────────────
    response = QueryResponse(
        status="success",
        question=question,
        db_type=DB_TYPE,
        sql=str(query_context) if DB_TYPE in ("sqlite", "postgres", "mysql") else None,
        answer=answer,
        key_insights=key_insights,
        charts=charts,
        data=result["data"],
        row_count=result["row_count"],
        self_healed=self_healed,
        message=None,
    )

    # ── Step 5: Save to session history ──────────────────────
    _session_history.append({
        "question":    question,
        "db_type":     DB_TYPE,
        "sql":         response.sql,
        "answer":      answer,
        "key_insights": key_insights,
        "charts":      [c.dict() for c in charts],
        "row_count":   result["row_count"],
        "self_healed": self_healed,
    })

    return response