# core/visualizer.py

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

matplotlib.use('TkAgg')

def execute_chart_code(code: str, results: list) -> dict:
    """
    Executes LLM-generated matplotlib code with the query results.
    """
    try:
        # Strip markdown backticks if Groq wrapped the code
        if code.startswith("```"):
            code = code.split("\n", 1)[1]  # remove first line (```python)
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]  # remove last ```
        code = code.strip()

        # Clean environment for execution
        exec_globals = {
            "results": results,
            "plt": plt,
            "sns": sns,
        }

        exec(code, exec_globals)

        return {"status": "success"}

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }