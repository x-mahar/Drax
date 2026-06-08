import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from core.schema_router import get_pruned_schema

client = Groq(api_key=GROQ_API_KEY)


def build_prompt(user_query: str) -> str:
    return f"""
You are an expert SQL assistant. Convert the user's natural language question into a valid SQL query.

Database Schema:
{get_pruned_schema(user_query)}

Rules:
- Return ONLY the raw SQL query, nothing else
- No explanations, no markdown, no backticks
- Only use SELECT statements
- Use exact column and table names from the schema above
- ALWAYS include the aggregated value (SUM, COUNT, AVG) in SELECT, never just the group-by column alone
- For ranking/top/highest/lowest questions always return TOP 10 rows not just 1

User Question: {user_query}

SQL Query:
"""


def generate_sql(user_query: str) -> dict:
    try:
        prompt = build_prompt(user_query)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=256,
        )
        sql = response.choices[0].message.content.strip()
        return {"status": "success", "sql": sql}
    except Exception as e:
        return {"status": "error", "sql": None, "message": str(e)}


def regenerate_sql(user_query: str, bad_sql: str, problem: str) -> dict:
    try:
        prompt = f"""
You are an expert SQL debugger.

The following SQL query was generated for this question but produced a wrong or incomplete result.

User Question: {user_query}

Database Schema:
{get_pruned_schema(user_query)}

SQL That Failed or Returned Too Few Rows:
{bad_sql}

Problem:
{problem}

Fix the SQL query so it returns meaningful results.

Rules:
- Return ONLY the corrected raw SQL query, nothing else
- No explanations, no markdown, no backticks
- Only SELECT statements allowed
- Use exact column and table names from the schema above
- ALWAYS include aggregated values (SUM, COUNT, AVG) in SELECT
- For ranking/top/highest/lowest questions return TOP 10 rows not just 1
- If the problem is a missing JOIN, add the correct JOIN based on foreign keys in the schema
- If the problem is a wrong column name, use the exact name from the schema

Corrected SQL Query:
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        sql = response.choices[0].message.content.strip()
        return {"status": "success", "sql": sql}
    except Exception as e:
        return {"status": "error", "sql": None, "message": str(e)}


def generate_answer(user_query: str, query: str, results: list) -> dict:
    try:
        sample_results = results[:50]

        prompt = f"""
You are a Business Intelligence assistant helping analyze data.

Database Schema:
{get_pruned_schema(user_query)}

User Question: {user_query}

Query Executed:
{query}

Query Results (sample of {len(results)} total rows):
{sample_results}

Total rows returned: {len(results)}

Your job is to analyze the results and return a structured business summary.

Rules:
- Return ONLY a valid JSON object, no markdown, no backticks, no explanation
- Use INR for currency (Indian Rupees)
- Be precise and number-driven, not descriptive
- Use "Total rows returned" value for counts
- Prioritize insights in this exact order:
    1. Total Revenue (always first if revenue exists)
    2. Count / Number of records
    3. Highest or Lowest values
    4. Repeat customers or patterns (if any)

Return this exact JSON format:
{{
  "answer": "One crisp business-focused sentence. Must include total revenue and count if available.",
  "key_insights": [
    "Total Revenue: INR XXXX",
    "Number of Sales: X",
    "Highest Sale: INR XXXX (Product)",
    "add more only if genuinely useful"
  ]
}}

Do NOT add vague insights like 'sales were recorded'. Every insight must have a number.
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {
            "status": "success",
            "answer": parsed.get("answer", ""),
            "key_insights": parsed.get("key_insights", [])
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def is_data_question(user_query: str) -> bool:
    try:
        prompt = f"""
You are a query intent classifier for a data system.

Database Schema:
{get_pruned_schema(user_query)}

The user wants to analyze, visualize, or explore the data described in the schema above.
Answer YES only if the question clearly asks about analyzing, summarizing, comparing,
visualizing, or exploring concepts directly related to the fields in the schema above
(e.g. "profit" means revenue, "dashboard" means charts, "overview" means summary).
Answer NO for:
- Greetings or small talk (hi, hello, thanks)
- Single words or short phrases that are not data concepts (exil, asdf, ok, bye)
- Typos or gibberish that don't match any field or concept in the schema
- Off-topic questions unrelated to the schema
- Destructive requests (delete, drop, update)
- Anything ambiguous or unclear — if in doubt, answer NO.

User Input: "{user_query}"

Reply with ONLY one word — YES or NO.
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer == "YES"
    except:
        return True


def generate_chart_data(user_query: str, query: str, results: list) -> dict:
    """
    Phase 4 — replaces generate_chart_code.

    Instead of generating matplotlib Python code,
    this returns structured JSON that React/Recharts can consume directly.

    The LLM decides:
      - Best chart type for the data (bar, line, pie, scatter, horizontal_bar)
      - Which column is X axis
      - Which column(s) are Y axis
      - A human-readable title for each chart

    Returns up to 2 charts so the UI can show a richer dashboard.
    Also still generates matplotlib code for the CLI fallback.
    """
    try:
        sample_results = results[:50]
        columns = list(results[0].keys()) if results else []

        prompt = f"""
You are a data visualization expert building a BI dashboard.

A user asked: "{user_query}"

Query results columns: {columns}
Sample data (first 5 rows): {sample_results[:5]}
Total rows: {len(results)}

Your job is to decide the best way to visualize this data.

Rules:
- Return ONLY a valid JSON object, no markdown, no backticks, no explanation
- Pick 1 or 2 charts that best represent the data
- For each chart pick the most insightful type from: bar, line, pie, scatter, horizontal_bar
- Use "bar" for category comparisons
- Use "line" for time-series or trends
- Use "pie" for distribution/share (only when <= 8 categories)
- Use "horizontal_bar" for rankings with long labels
- Use "scatter" for correlation between two numeric columns
- x_key must be a string/category column from the data
- y_key must be a numeric column from the data
- title should be a short human-readable chart title

Return this exact format:
{{
  "charts": [
    {{
      "type": "bar",
      "title": "Revenue by Category",
      "x_key": "category_name",
      "y_key": "total_revenue",
      "x_label": "Category",
      "y_label": "Revenue (INR)"
    }},
    {{
      "type": "pie",
      "title": "Revenue Share by Category",
      "x_key": "category_name",
      "y_key": "total_revenue",
      "x_label": "Category",
      "y_label": "Share"
    }}
  ]
}}
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)

        return {
            "status":  "success",
            "charts":  parsed.get("charts", []),
            "data":    results,           # full data, React renders from this
        }

    except Exception as e:
        return {"status": "error", "charts": [], "data": [], "message": str(e)}


def generate_matplotlib(user_query: str, query: str, results: list) -> dict:
    """
    CLI fallback — kept for terminal use.
    Generates matplotlib 2x2 dashboard code exactly as before.
    """
    try:
        sample_results = results[:50]

        prompt = f"""
You are a Python data visualization expert building a BI dashboard.

A user asked: "{user_query}"

The following query was executed:
{query}

The results are (sample of {len(results)} total rows):
{sample_results}

Write Python matplotlib code that creates a 2x2 subplot dashboard in ONE figure window.

Layout:
- fig, axes = plt.subplots(2, 2, figsize=(14, 10))
- Create 4 subplots, each showing a DIFFERENT angle of the data
- Each subplot MUST use a DIFFERENT chart type — no two subplots can use the same chart type
- Choose the most insightful chart type for each angle from: barplot, horizontal barplot, pie, line, scatter
- CRITICAL: pie charts MUST use axes[row,col].pie() — seaborn has no pie chart, never use sns.pie()
- CRITICAL: line charts MUST use axes[row,col].plot() — never use sns.line()
- CRITICAL: horizontal bar MUST use axes[row,col].barh() — never use sns.barh()
- Only use sns. prefix for: sns.barplot(), sns.scatterplot()

Rules:
- Use ONLY matplotlib and seaborn (no other libraries)
- The data is already available as a Python list of dicts called `results`
- Always aggregate before plotting — never plot individual rows
- Use ax= parameter for seaborn plots
- Format Y axis: use 'M' for millions, 'K' for thousands
- Add title, x-label, y-label to each subplot
- Use INR for currency labels
- Use this exact style: plt.style.use("seaborn-v0_8")
- Set main title: fig.suptitle("{user_query.title()}", fontsize=16, fontweight='bold')
- End with plt.tight_layout() and plt.show()
- Return ONLY raw Python code, no markdown, no backticks, no explanation
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2048,
        )
        code = response.choices[0].message.content.strip()
        return {"status": "success", "code": code}
    except Exception as e:
        return {"status": "error", "code": None, "message": str(e)}


def generate_mongo_query(user_query: str) -> dict:
    try:
        prompt = f"""
You are an expert MongoDB query assistant.

Database Schema:
{get_pruned_schema(user_query)}

Convert the user's natural language question into a MongoDB query.
Use the exact collection name and field names from the schema above.

Rules:
- Return ONLY a valid JSON object, no markdown, no backticks, no explanation
- Use either "find" or "aggregate" operation
- For simple filters use "find", for grouping/totals use "aggregate"
- Always exclude _id from results

For "find" return this format:
{{
  "operation": "find",
  "params": {{
    "filter": {{}},
    "projection": {{"_id": 0}},
    "limit": 0
  }}
}}

For "aggregate" return this format:
{{
  "operation": "aggregate",
  "params": {{
    "pipeline": []
  }}
}}

User Question: {user_query}
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {"status": "success", "query": parsed}
    except Exception as e:
        return {"status": "error", "query": None, "message": str(e)}


def generate_redis_query(user_query: str) -> dict:
    try:
        prompt = f"""
You are an expert Redis query assistant.

Database Schema:
{get_pruned_schema(user_query)}

Convert the user's natural language question into a Redis query dict.
Use the exact key patterns and field names from the schema above.

Supported operations:
1. get_all — fetch all records
2. filter_by — filter by a field value
3. top_by_revenue — get top N by revenue
4. group_by — group by a field and sum revenue

Rules:
- Return ONLY a valid JSON object, no markdown, no backticks
- Pick the most appropriate operation for the question

Return this format:
{{
  "operation": "operation_name",
  "params": {{}}
}}

User Question: {user_query}
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {"status": "success", "query": parsed}
    except Exception as e:
        return {"status": "error", "query": None, "message": str(e)}


def generate_chroma_query(user_query: str) -> dict:
    try:
        prompt = f"""
You are an expert ChromaDB query assistant.

Database Schema:
{get_pruned_schema(user_query)}

Convert the user's natural language question into a ChromaDB query dict.
Use the exact collection name and metadata field names from the schema above.

Supported operations:

1. semantic_search — use when the user asks in natural language, wants similar records,
   or asks about a concept (e.g. "high value sales", "laptop deals")
   Params: query_text (string), n_results (int, default 5), where (optional metadata filter dict)

2. get_all — use when user wants to see everything ("show all sales", "list all records")
   Params: limit (int, optional)

3. get_by_id — use when user asks for a specific record by ID
   Params: ids (list of strings, e.g. ["1", "3"])

Rules:
- Return ONLY a valid JSON object, no markdown, no backticks, no explanation
- For "where" filters use exact field names from the schema
- ChromaDB "where" syntax: {{"field": {{"$eq": "value"}}}} for equality
- For revenue comparisons use: {{"revenue": {{"$gte": 1000.0}}}}
- Prefer semantic_search for most questions
- n_results should match what the user asked for (default 5, max 10)

Return this format:
{{
  "operation": "operation_name",
  "params": {{}}
}}

User Question: {user_query}
"""
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {"status": "success", "query": parsed}
    except Exception as e:
        return {"status": "error", "query": None, "message": str(e)}