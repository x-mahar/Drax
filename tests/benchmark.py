# tests/benchmark.py
#
# Runs all test questions against the active DB, measures response time,
# and logs pass/fail for each query.
#
# Run with:
#   python -m tests.benchmark
#
# Output:
#   - Live results in terminal
#   - tests/benchmark_results.json  (full log)
#   - tests/benchmark_summary.txt   (human-readable report)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from datetime import datetime
from config import DB_TYPE

# ── Import the right executor ─────────────────────────────────
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

from llm.groq_client import generate_sql, regenerate_sql, is_data_question
from core.validator import validate_sql

# ── Test questions ────────────────────────────────────────────
# Organized by complexity tier
# expected_min_rows: minimum rows we expect back for pass/fail

TEST_QUESTIONS = [

    # ── Tier 1: Single Table ──────────────────────────────────
    {
        "tier": 1,
        "label": "Single Table",
        "question": "show all products in Electronics category",
        "expected_min_rows": 3,
    },
    {
        "tier": 1,
        "label": "Single Table",
        "question": "list all stores in North region",
        "expected_min_rows": 1,
    },
    {
        "tier": 1,
        "label": "Single Table",
        "question": "show all employees in Sales department",
        "expected_min_rows": 1,
    },
    {
        "tier": 1,
        "label": "Single Table",
        "question": "which warehouses are running low on stock",
        "expected_min_rows": 1,
    },

    # ── Tier 2: 2-3 Table Joins ───────────────────────────────
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "which customers placed the most orders",
        "expected_min_rows": 5,
    },
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "show total revenue by product category",
        "expected_min_rows": 5,
    },
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "top 10 customers by total amount spent",
        "expected_min_rows": 5,
    },
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "which brand has the highest selling products",
        "expected_min_rows": 3,
    },
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "show all orders with payment status Failed",
        "expected_min_rows": 1,
    },
    {
        "tier": 2,
        "label": "2-3 Table Join",
        "question": "which region has the highest number of orders",
        "expected_min_rows": 3,
    },

    # ── Tier 3: 4-5 Table Joins ───────────────────────────────
    {
        "tier": 3,
        "label": "4-5 Table Join",
        "question": "show revenue by customer segment and region",
        "expected_min_rows": 3,
    },
    {
        "tier": 3,
        "label": "4-5 Table Join",
        "question": "which store sold the most Electronics products",
        "expected_min_rows": 3,
    },
    {
        "tier": 3,
        "label": "4-5 Table Join",
        "question": "top 5 products by revenue across all order items",
        "expected_min_rows": 3,
    },
    {
        "tier": 3,
        "label": "4-5 Table Join",
        "question": "show monthly revenue trend for year 2024",
        "expected_min_rows": 6,
    },
    {
        "tier": 3,
        "label": "4-5 Table Join",
        "question": "which customers returned the most items",
        "expected_min_rows": 3,
    },

    # ── Tier 4: Deep Joins 6+ Tables ─────────────────────────
    {
        "tier": 4,
        "label": "Deep Join 6+",
        "question": "show total revenue by brand for completed orders only",
        "expected_min_rows": 3,
    },
    {
        "tier": 4,
        "label": "Deep Join 6+",
        "question": "which department employees work in the highest revenue stores",
        "expected_min_rows": 3,
    },
    {
        "tier": 4,
        "label": "Deep Join 6+",
        "question": "compare online vs in-store revenue by product category",
        "expected_min_rows": 3,
    },
    {
        "tier": 4,
        "label": "Deep Join 6+",
        "question": "show top 10 customers by revenue who never returned any item",
        "expected_min_rows": 3,
    },
    {
        "tier": 4,
        "label": "Deep Join 6+",
        "question": "which warehouse region has the lowest stock for top selling products",
        "expected_min_rows": 3,
    },

    # ── Tier 5: Aggregation + Business ───────────────────────
    {
        "tier": 5,
        "label": "Aggregation",
        "question": "what is the average order value by channel",
        "expected_min_rows": 2,
    },
    {
        "tier": 5,
        "label": "Aggregation",
        "question": "show revenue growth month over month for 2023 vs 2024",
        "expected_min_rows": 6,
    },
    {
        "tier": 5,
        "label": "Aggregation",
        "question": "which payment method is most popular among premium segment customers",
        "expected_min_rows": 2,
    },
    {
        "tier": 5,
        "label": "Aggregation",
        "question": "show products with high return rate",
        "expected_min_rows": 3,
    },
    {
        "tier": 5,
        "label": "Aggregation",
        "question": "what percentage of orders were cancelled by region",
        "expected_min_rows": 3,
    },
]

SINGLE_ROW_KEYWORDS = ["total", "average", "how many", "count", "sum", "overall"]


def _expects_multiple_rows(question: str) -> bool:
    q = question.lower()
    return not any(kw in q for kw in SINGLE_ROW_KEYWORDS)


def run_benchmark():
    print("=" * 60)
    print(f"BENCHMARK — DB: {DB_TYPE.upper()} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []
    total = len(TEST_QUESTIONS)
    passed = 0
    failed = 0
    healed = 0  # self-healed via regenerate_sql

    for i, test in enumerate(TEST_QUESTIONS, 1):
        question    = test["question"]
        min_rows    = test["expected_min_rows"]
        tier        = test["tier"]
        label       = test["label"]

        print(f"\n[{i:02d}/{total}] T{tier} | {label}")
        print(f"  Q: {question}")

        record = {
            "id":           i,
            "tier":         tier,
            "label":        label,
            "question":     question,
            "expected_min_rows": min_rows,
            "sql":          None,
            "sql_healed":   None,
            "row_count":    0,
            "response_time_ms": 0,
            "self_healed":  False,
            "status":       "fail",
            "fail_reason":  None,
        }

        start = time.time()

        try:
            # Step 1 — generate SQL
            llm_response = generate_sql(question)
            if llm_response["status"] == "error":
                record["fail_reason"] = f"LLM error: {llm_response['message']}"
                _print_fail(record["fail_reason"])
                failed += 1
                results.append(record)
                continue

            sql = llm_response["sql"]
            record["sql"] = sql

            # Step 2 — validate
            validation = validate_sql(sql)
            if not validation["is_valid"]:
                record["fail_reason"] = f"Validation: {validation['message']}"
                _print_fail(record["fail_reason"])
                failed += 1
                results.append(record)
                continue

            # Step 3 — execute
            result = execute_query(sql)

            # Step 4 — self-heal if needed
            if result["status"] == "error":
                print(f"  ⚠️  DB error — triggering self-heal...")
                fix = regenerate_sql(
                    question, bad_sql=sql,
                    problem=f"DB error: {result['message']}"
                )
                if fix["status"] == "success":
                    sql = fix["sql"]
                    record["sql_healed"] = sql
                    record["self_healed"] = True
                    healed += 1
                    result = execute_query(sql)

            elif result["row_count"] <= 1 and _expects_multiple_rows(question):
                print(f"  ⚠️  Only {result['row_count']} row(s) — triggering self-heal...")
                fix = regenerate_sql(
                    question, bad_sql=sql,
                    problem=(
                        f"Returned only {result['row_count']} row(s). "
                        f"Expected multiple. Fix JOINs and GROUP BY."
                    )
                )
                if fix["status"] == "success":
                    sql = fix["sql"]
                    record["sql_healed"] = sql
                    record["self_healed"] = True
                    healed += 1
                    result = execute_query(sql)

            elapsed_ms = round((time.time() - start) * 1000)
            record["response_time_ms"] = elapsed_ms
            record["row_count"] = result.get("row_count", 0)

            # Step 5 — evaluate pass/fail
            if result["status"] == "error":
                record["fail_reason"] = f"DB error after heal: {result['message']}"
                _print_fail(record["fail_reason"], elapsed_ms)
                failed += 1

            elif result["row_count"] < min_rows:
                record["fail_reason"] = (
                    f"Too few rows: got {result['row_count']}, expected >= {min_rows}"
                )
                _print_fail(record["fail_reason"], elapsed_ms)
                failed += 1

            else:
                record["status"] = "pass"
                healed_tag = " (self-healed)" if record["self_healed"] else ""
                print(f"  ✅ PASS{healed_tag} | {result['row_count']} rows | {elapsed_ms}ms")
                passed += 1

        except Exception as e:
            elapsed_ms = round((time.time() - start) * 1000)
            record["response_time_ms"] = elapsed_ms
            record["fail_reason"] = f"Exception: {str(e)}"
            _print_fail(record["fail_reason"], elapsed_ms)
            failed += 1

        results.append(record)

    # ── Summary ───────────────────────────────────────────────
    total_time = sum(r["response_time_ms"] for r in results)
    avg_time   = round(total_time / total) if total else 0
    pass_rate  = round((passed / total) * 100) if total else 0

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"  Total Questions : {total}")
    print(f"  Passed          : {passed} ({pass_rate}%)")
    print(f"  Failed          : {failed}")
    print(f"  Self-Healed     : {healed}")
    print(f"  Avg Response    : {avg_time}ms")
    print(f"  Total Time      : {round(total_time/1000, 1)}s")

    # Per-tier summary
    print("\n  Results by Tier:")
    for tier_num in range(1, 6):
        tier_results = [r for r in results if r["tier"] == tier_num]
        if not tier_results:
            continue
        tier_passed = sum(1 for r in tier_results if r["status"] == "pass")
        tier_avg    = round(sum(r["response_time_ms"] for r in tier_results) / len(tier_results))
        tier_label  = tier_results[0]["label"]
        print(f"    T{tier_num} {tier_label:<20} {tier_passed}/{len(tier_results)} passed | avg {tier_avg}ms")

    # Failed questions
    failed_list = [r for r in results if r["status"] == "fail"]
    if failed_list:
        print("\n  Failed Questions:")
        for r in failed_list:
            print(f"    [{r['id']:02d}] {r['question']}")
            print(f"         Reason: {r['fail_reason']}")

    print("=" * 60)

    # ── Save results ──────────────────────────────────────────
    os.makedirs("tests", exist_ok=True)

    json_path = "tests/benchmark_results.json"
    with open(json_path, "w") as f:
        json.dump({
            "run_at":    datetime.now().isoformat(),
            "db_type":   DB_TYPE,
            "summary": {
                "total":    total,
                "passed":   passed,
                "failed":   failed,
                "healed":   healed,
                "pass_rate": pass_rate,
                "avg_response_ms": avg_time,
            },
            "results": results,
        }, f, indent=2)

    txt_path = "tests/benchmark_summary.txt"
    with open(txt_path, "w") as f:
        f.write(f"Benchmark Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"DB: {DB_TYPE.upper()}\n\n")
        f.write(f"Total : {total}\n")
        f.write(f"Passed: {passed} ({pass_rate}%)\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Healed: {healed}\n")
        f.write(f"Avg   : {avg_time}ms\n\n")
        for r in results:
            status = "PASS" if r["status"] == "pass" else "FAIL"
            healed_tag = " [healed]" if r["self_healed"] else ""
            f.write(f"[{status}]{healed_tag} T{r['tier']} | {r['question']}\n")
            f.write(f"  rows={r['row_count']} time={r['response_time_ms']}ms\n")
            if r["fail_reason"]:
                f.write(f"  reason: {r['fail_reason']}\n")
            f.write("\n")

    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {txt_path}\n")


def _print_fail(reason: str, elapsed_ms: int = 0):
    time_str = f" | {elapsed_ms}ms" if elapsed_ms else ""
    print(f"  ❌ FAIL{time_str} — {reason}")


if __name__ == "__main__":
    run_benchmark()