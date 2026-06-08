# core/schema_router.py

import numpy as np
from sentence_transformers import SentenceTransformer

_model = None
_index = {}  # { block_name: { "text": str, "vec": np.ndarray } }


def build_index(schema_text: str):
    """
    Call once on startup (from config.py) with the full DB_SCHEMA string.
    Splits it into per-table blocks and embeds each one.
    """
    global _model, _index
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    blocks = [b.strip() for b in schema_text.split("\n\n") if b.strip()]
    for block in blocks:
        name = block.split("\n")[0]  # e.g. "Table: orders (10 rows)"
        _index[name] = {
            "text": block,
            "vec":  _model.encode(block, convert_to_numpy=True)
        }
    print(f"[schema_router] Indexed {len(_index)} blocks.")


def get_pruned_schema(question: str, top_k: int = 5) -> str:
    """
    Returns schema text for only the top_k most relevant table blocks.
    Called inside every groq_client generate_ function.
    """
    if not _index:
        raise RuntimeError("Schema index not built. Call build_index() first.")

    q_vec  = _model.encode(question, convert_to_numpy=True)
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)

    scores = {}
    for name, meta in _index.items():
        v = meta["vec"]
        scores[name] = float(np.dot(q_norm, v / (np.linalg.norm(v) + 1e-10)))

    top = sorted(scores, key=scores.get, reverse=True)[:top_k]
    print(f"[schema_router] Selected: {top}")
    return "\n\n".join(_index[t]["text"] for t in top)