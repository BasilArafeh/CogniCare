# Combine vector search and keyword search
"""
bm25.py
-------
Standalone BM25 sparse-retrieval module for CogniCare RAG pipeline.

Improvements over the original inline implementation:
  1. Medical-aware tokenizer  — regex-based, strips stopwords, handles
     hyphenated terms and dosage numbers (e.g. "10mg").
  2. Stopword filtering       — common English words removed before
     indexing so IDF scores reflect real medical term frequency.
  3. Per-drug index caching   — BM25 objects are built once per
     (generic_name, chunk_types) pair and reused across queries via
     an LRU cache, eliminating redundant ChromaDB fetches + rebuilds.
  4. Clean public API         — bm25_retrieve() is the only symbol the
     pipeline needs to import.
"""

import re
import math
import hashlib
from collections import Counter
from functools import lru_cache

import chromadb

# ── STOPWORDS ──────────────────────────────────────────────────────────────────
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "it", "in", "of", "to", "and", "or", "for",
    "be", "are", "was", "with", "this", "that", "as", "at", "by", "from",
    "on", "not", "but", "if", "its", "also", "may", "can", "should",
    "will", "which", "when", "have", "has", "had", "do", "does", "did",
    "been", "being", "than", "then", "so", "no", "up", "how", "what",
    "who", "more", "other", "used", "use", "such",
})


# ── TOKENIZER ─────────────────────────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """
    Medical-aware tokenizer.

    - Lower-cases the entire string.
    - Extracts alphanumeric tokens (including apostrophes for contractions
      and hyphen-joined compounds like "anti-inflammatory").
    - Keeps dosage tokens like "10mg", "500mcg", "2.5ml".
    - Removes stopwords and single-character tokens.

    Examples
    --------
    >>> tokenize("What are the side-effects of 10mg Lisinopril?")
    ['side-effects', '10mg', 'lisinopril']
    """
    tokens = re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


# ── BM25 ───────────────────────────────────────────────────────────────────────
class BM25:
    """
    Okapi BM25 (k1=1.5, b=0.75) with improved tokenization.

    Parameters
    ----------
    corpus : list[str]
        Raw document strings to index.
    k1 : float
        Term-frequency saturation parameter (default 1.5).
    b : float
        Length normalisation parameter (default 0.75).
    """

    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b  = b
        self.n  = len(corpus)

        self.tokenized: list[list[str]] = [tokenize(doc) for doc in corpus]
        self.avgdl: float = (
            sum(len(d) for d in self.tokenized) / max(1, self.n)
        )

        # Document frequency
        df: dict[str, int] = {}
        for doc_tokens in self.tokenized:
            for term in set(doc_tokens):
                df[term] = df.get(term, 0) + 1

        # IDF — always non-negative: log((N - df + 0.5) / (df + 0.5) + 1)
        self.idf: dict[str, float] = {
            t: math.log((self.n - f + 0.5) / (f + 0.5) + 1)
            for t, f in df.items()
        }

        self.tf: list[Counter] = [Counter(tokens) for tokens in self.tokenized]

    def get_scores(self, query: str) -> list[float]:
        """Return a BM25 score for every document in the corpus."""
        query_tokens = tokenize(query)
        scores = [0.0] * self.n

        for token in query_tokens:
            idf = self.idf.get(token, 0.0)
            if idf == 0.0:
                continue
            for i, (tf_d, doc_tokens) in enumerate(zip(self.tf, self.tokenized)):
                tf = tf_d.get(token, 0)
                if tf == 0:
                    continue
                dl  = len(doc_tokens)
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[i] += idf * num / den

        return scores

    def top_n(self, query: str, n: int) -> list[int]:
        """Return indices of the top-n highest-scoring documents."""
        scores = self.get_scores(query)
        return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]


# ── CACHE ──────────────────────────────────────────────────────────────────────
# Keyed by (generic_name, chunk_types_tuple) so that different chunk-type
# filters for the same drug each get their own cached index.
# maxsize=128 covers 17 high-chunk drugs × ~7 chunk-type combos with headroom.

@lru_cache(maxsize=128)
def _build_cached_index(
    collection_name: str,
    chroma_path: str,
    generic_name: str,
    chunk_types_tuple: tuple[str, ...] | None,
) -> tuple[BM25, list[str], list[dict]] | None:
    """
    Fetch a per-drug sub-corpus from ChromaDB once and cache the BM25 index.

    Returns (bm25_index, docs, metas) or None if the corpus is empty / on error.

    Notes
    -----
    chromadb.PersistentClient is intentionally created inside this cached
    function so we hold a reference only when needed.  The lru_cache ensures
    this is called at most once per unique (collection, drug, chunk_types) combo.
    """
    try:
        client     = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(collection_name)
    except Exception:
        return None

    conditions: list[dict] = [{"generic_name": {"$eq": generic_name}}]
    if chunk_types_tuple:
        conditions.append({"chunk_type": {"$in": list(chunk_types_tuple)}})

    where = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    try:
        result = collection.get(
            where=where,
            include=["documents", "metadatas"],
            limit=2000,
        )
    except Exception:
        return None

    docs  = result["documents"]
    metas = result["metadatas"]

    if not docs:
        return None

    index = BM25(docs)
    return index, docs, metas


# ── PUBLIC API ─────────────────────────────────────────────────────────────────
def bm25_retrieve(
    query: str,
    generic_name: str | None,
    chunk_types: list[str] | None,
    n: int,
    *,
    collection_name: str,
    chroma_path: str,
) -> tuple[list[str], list[dict]]:
    """
    BM25 sparse retrieval over a per-drug ChromaDB sub-corpus.

    Parameters
    ----------
    query : str
        The (possibly rewritten) search query.
    generic_name : str | None
        Drug to restrict the sub-corpus to.  Returns ([], []) when None
        because a full 36k-doc scan would be too slow.
    chunk_types : list[str] | None
        Optional metadata filter on chunk_type.
    n : int
        Number of top results to return.
    collection_name : str
        ChromaDB collection to query (passed through to the cache key).
    chroma_path : str
        Path to the ChromaDB persistent store.

    Returns
    -------
    (docs, metas) — parallel lists of length <= n.
    """
    if not generic_name:
        return [], []

    # Convert chunk_types to a hashable tuple for the lru_cache key
    chunk_key: tuple[str, ...] | None = (
        tuple(sorted(chunk_types)) if chunk_types else None
    )

    cached = _build_cached_index(collection_name, chroma_path, generic_name, chunk_key)
    if cached is None:
        return [], []

    index, docs, metas = cached
    indices = index.top_n(query, n)
    return [docs[i] for i in indices], [metas[i] for i in indices]


# ── HELPERS re-exported for pipeline ──────────────────────────────────────────
def cid(doc: str) -> str:
    """MD5 fingerprint — used by the pipeline for cross-list deduplication."""
    return hashlib.md5(doc.encode()).hexdigest()