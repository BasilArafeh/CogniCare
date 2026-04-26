"""
reranker.py — upgraded to bge-reranker-v2-m3
"""

BGE_MODEL    = "BAAI/bge-reranker-v2-m3"
BGE_USE_FP16 = False

_bge_reranker = None

def _get_reranker():
    global _bge_reranker
    if _bge_reranker is None:
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as e:
            raise ImportError("Run: pip install FlagEmbedding") from e
        print(f"[reranker] Loading {BGE_MODEL}...")
        _bge_reranker = FlagReranker(BGE_MODEL, use_fp16=BGE_USE_FP16)
        print("[reranker] Model loaded.")
    return _bge_reranker

def _rerank_bge(query: str, docs: list[str], top_n: int) -> list[int]:
    reranker = _get_reranker()
    pairs    = [[query, doc] for doc in docs]
    scores   = reranker.compute_score(pairs, normalize=True, batch_size=8)
    ranked   = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return ranked[:top_n]

def rerank(query: str, docs: list[str], metas: list[dict], top_n: int) -> tuple[list[str], list[dict]]:
    if not docs or top_n >= len(docs):
        return docs[:top_n], metas[:top_n]
    try:
        indices = _rerank_bge(query, docs, top_n)
    except Exception as e:
        print(f"[reranker] WARNING: {e}. Falling back to original order.")
        return docs[:top_n], metas[:top_n]
    return [docs[i] for i in indices], [metas[i] for i in indices]