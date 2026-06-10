# core/schema_router.py

import os
import json
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer

_model = None
_index = {}

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".schema_cache.json")


def _schema_hash(schema_text: str) -> str:
    return hashlib.md5(schema_text.encode()).hexdigest()


def _load_embedding_cache(schema_hash: str) -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            if data.get("hash") == schema_hash:
                print(f"[schema_router] Loaded embeddings from disk cache.")
                return {
                    k: {"text": v["text"], "vec": np.array(v["vec"], dtype=np.float32)}
                    for k, v in data["index"].items()
                }
    except Exception as e:
        print(f"[schema_router] Cache load error: {e}")
    return {}


def _save_embedding_cache(schema_hash: str, index: dict):
    try:
        data = {
            "hash": schema_hash,
            "index": {
                k: {"text": v["text"], "vec": v["vec"].tolist()}
                for k, v in index.items()
            }
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
        print(f"[schema_router] Saved embeddings to disk cache.")
    except Exception as e:
        print(f"[schema_router] Cache save error: {e}")


def build_index(schema_text: str):
    global _model, _index

    schema_hash = _schema_hash(schema_text)

    # Try loading from disk cache first (skips model encode)
    cached = _load_embedding_cache(schema_hash)
    if cached:
        # Still need model for query encoding, but skip block encoding
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _index = cached
        print(f"[schema_router] Indexed {len(_index)} blocks (from cache).")
        return

    # First time — encode all blocks and save to disk
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    blocks = [b.strip() for b in schema_text.split("\n\n") if b.strip()]
    for block in blocks:
        name = block.split("\n")[0]
        _index[name] = {
            "text": block,
            "vec":  _model.encode(block, convert_to_numpy=True)
        }

    _save_embedding_cache(schema_hash, _index)
    print(f"[schema_router] Indexed {len(_index)} blocks.")


def get_pruned_schema(question: str, top_k: int = 5) -> str:
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