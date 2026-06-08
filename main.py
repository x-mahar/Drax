import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import os
from datetime import datetime
from llm.groq_client import (
    generate_sql, regenerate_sql, generate_mongo_query, generate_redis_query,
    generate_chroma_query, generate_answer, is_data_question,
    generate_chart_data, generate_matplotlib
)
from core.validator import validate_sql
from core.visualizer import execute_chart_code
from config import DB_TYPE

# Auto pick the right DB
if DB_TYPE == "sqlite":
    from database.db import execute_query, print_results
elif DB_TYPE == "postgres":
    from database.db_postgres import execute_query, print_results
elif DB_TYPE == "mongo":
    from database.db_mongo import execute_query, print_results
elif DB_TYPE == "mysql":
    from database.db_mysql import execute_query, print_results
elif DB_TYPE == "redis":
    from database.db_redis import execute_query, print_results
elif DB_TYPE == "chroma":
    from database.db_chroma import execute_query, print_results

SINGLE_ROW_KEYWORDS = ["total", "average", "how many", "count", "sum", "overall"]


def _expects_multiple_rows(question: str) -> bool:
    q = question.lower()
    return not any(kw in q for kw in SINGLE_ROW_KEYWORDS)


def _save_chart_history(history: list):
    """Saves session chart history to charts/session_history.json"""
    os.makedirs("charts", exist_ok=True)
    path = "charts/session_history.json"
    with open(path, "w") as f:
        json.dump(history, f, indent=2, default=str)


def main():
    print("=" * 50)
    print(f"NL to Any DB POC — Powered by Groq | DB: {DB_TYPE.upper()}")
    print("=" * 50)
    print("Type your question in plain English.")
    print("Type 'history' to see this session's queries.")
    print("Type 'exit' to quit.\n")

    # ── Session chart history ─────────────────────────────────
    # Each entry: { question, sql, answer, key_insights, charts, data, timestamp }
    # This becomes the API response shape for the React UI
    session_history = []

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye!")
                _save_chart_history(session_history)
                print(f"Session history saved to charts/session_history.json")
                break

            if user_input.lower() == "history":
                if not session_history:
                    print("\nNo queries yet this session.\n")
                else:
                    print(f"\n── Session History ({len(session_history)} queries) ──")
                    for i, h in enumerate(session_history, 1):
                        print(f"  {i}. [{h['timestamp']}] {h['question']}")
                        print(f"     rows={h['row_count']} charts={len(h['charts'])}")
                    print()
                continue

            if not user_input:
                continue

            print("\nChecking your question...")
            if not is_data_question(user_input):
                print("\nThat doesn't look like a data question.")
                print("Try something like:")
                print("   - 'show all sales from North region'")
                print("   - 'top 5 customers by revenue'")
                print("   - 'total revenue by product'\n")
                continue

            # ── ChromaDB Flow ─────────────────────────────────────
            if DB_TYPE == "chroma":
                print("\nGenerating ChromaDB query...")
                chroma_response = generate_chroma_query(user_input)
                if chroma_response["status"] == "error":
                    print(f"\nLLM Error: {chroma_response['message']}")
                    continue
                chroma_query = chroma_response["query"]
                print(f"\nGenerated Query:\n{json.dumps(chroma_query, indent=2)}")
                result = execute_query(chroma_query)
                if result["status"] == "error":
                    print(f"\nQuery Error: {result['message']}")
                    continue
                query_context = chroma_query

            # ── MongoDB Flow ──────────────────────────────────────
            elif DB_TYPE == "mongo":
                print("\nGenerating MongoDB query...")
                mongo_response = generate_mongo_query(user_input)
                if mongo_response["status"] == "error":
                    print(f"\nLLM Error: {mongo_response['message']}")
                    continue
                mongo_query = mongo_response["query"]
                print(f"\nGenerated Query:\n{json.dumps(mongo_query, indent=2)}")
                result = execute_query(mongo_query)
                if result["status"] == "error":
                    print(f"\nQuery Error: {result['message']}")
                    continue
                query_context = mongo_query

            # ── Redis Flow ────────────────────────────────────────
            elif DB_TYPE == "redis":
                print("\nGenerating Redis query...")
                redis_response = generate_redis_query(user_input)
                if redis_response["status"] == "error":
                    print(f"\nLLM Error: {redis_response['message']}")
                    continue
                redis_query = redis_response["query"]
                print(f"\nGenerated Query:\n{json.dumps(redis_query, indent=2)}")
                result = execute_query(redis_query)
                if result["status"] == "error":
                    print(f"\nQuery Error: {result['message']}")
                    continue
                query_context = redis_query

            # ── SQL Flow (SQLite / PostgreSQL / MySQL) ────────────
            else:
                print("\nGenerating SQL...")
                llm_response = generate_sql(user_input)
                if llm_response["status"] == "error":
                    print(f"\nLLM Error: {llm_response['message']}")
                    continue

                sql = llm_response["sql"]

                validation = validate_sql(sql)
                if not validation["is_valid"]:
                    print(f"\nValidation: {validation['message']}")
                    continue

                result = execute_query(sql)

                # ── Self-Healing Layer ────────────────────────────
                if result["status"] == "error":
                    print(f"\n⚠️  Query failed: {result['message']}")
                    print("🔁 Self-healing: re-prompting LLM with error context...")
                    fix_response = regenerate_sql(
                        user_input, bad_sql=sql,
                        problem=f"DB execution error: {result['message']}"
                    )
                    if fix_response["status"] == "error":
                        print(f"\nLLM Error on retry: {fix_response['message']}")
                        continue
                    sql = fix_response["sql"]
                    validation = validate_sql(sql)
                    if not validation["is_valid"]:
                        print(f"\nValidation on retry: {validation['message']}")
                        continue
                    result = execute_query(sql)
                    if result["status"] == "error":
                        print(f"\nQuery Error after retry: {result['message']}")
                        continue
                    print("✅ Self-healing succeeded.")

                elif result["row_count"] <= 1 and _expects_multiple_rows(user_input):
                    print(f"\n⚠️  Only {result['row_count']} row(s) returned — expected more.")
                    print("🔁 Self-healing: re-prompting LLM to fix query...")
                    fix_response = regenerate_sql(
                        user_input, bad_sql=sql,
                        problem=(
                            f"Query returned only {result['row_count']} row(s). "
                            f"Expected multiple rows. "
                            f"Likely cause: missing JOIN, wrong GROUP BY, or LIMIT 1. "
                            f"Fix it to return all relevant rows with aggregated values."
                        )
                    )
                    if fix_response["status"] == "error":
                        print(f"\nLLM Error on retry: {fix_response['message']}")
                        continue
                    sql = fix_response["sql"]
                    validation = validate_sql(sql)
                    if not validation["is_valid"]:
                        print(f"\nValidation on retry: {validation['message']}")
                        continue
                    result = execute_query(sql)
                    if result["status"] == "error":
                        print(f"\nQuery Error after retry: {result['message']}")
                        continue
                    print(f"✅ Self-healing succeeded. Got {result['row_count']} rows.")

                query_context = sql

            # ── Common Flow ───────────────────────────────────────

            print("\nAnalyzing results...")
            interpretation = generate_answer(user_input, query_context, result["data"])

            # ── Phase 4: Structured chart data (for React UI) ─────
            print("\nGenerating chart data...")
            chart_data_response = generate_chart_data(user_input, query_context, result["data"])

            # ── CLI: matplotlib fallback ──────────────────────────
            print("\nRendering chart...")
            mpl_response = generate_matplotlib(user_input, query_context, result["data"])
            if mpl_response["status"] == "success":
                chart_result = execute_chart_code(mpl_response["code"], result["data"])
                if chart_result["status"] == "error":
                    print(f"\nChart Error: {chart_result['message']}")
            else:
                print(f"\nChart generation failed: {mpl_response['message']}")

            # ── Add to session history ────────────────────────────
            history_entry = {
                "timestamp":   datetime.now().strftime("%H:%M:%S"),
                "question":    user_input,
                "sql":         query_context if DB_TYPE in ("sqlite", "postgres", "mysql") else None,
                "answer":      interpretation.get("answer", "") if interpretation["status"] == "success" else "",
                "key_insights": interpretation.get("key_insights", []) if interpretation["status"] == "success" else [],
                "charts":      chart_data_response.get("charts", []),
                "data":        result["data"],
                "row_count":   result["row_count"],
                "db_type":     DB_TYPE,
            }
            session_history.append(history_entry)

            # ── Display ───────────────────────────────────────────
            print("\n" + "=" * 50)

            if interpretation["status"] == "success":
                print(f"\nAnswer:\n{interpretation['answer']}")
                if interpretation["key_insights"]:
                    print("\nKey Insights:")
                    for i, insight in enumerate(interpretation["key_insights"], 1):
                        print(f"  {i}. {insight}")

            if chart_data_response["status"] == "success":
                print(f"\nChart Config ({len(chart_data_response['charts'])} charts):")
                for c in chart_data_response["charts"]:
                    print(f"  - {c['type'].upper()} | {c['title']} | x={c['x_key']} y={c['y_key']}")

            print(f"\nRaw Data ({result['row_count']} rows):")
            print(json.dumps(result["data"], indent=2, default=str))

            print(f"\nSession queries so far: {len(session_history)}")
            print("\n" + "=" * 50 + "\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            _save_chart_history(session_history)
            break


if __name__ == "__main__":
    main()