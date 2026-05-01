"""
ragas_doc_eval.py  —  CogniCare Document RAG Evaluation

Evaluates the documents pipeline (Alzheimer's guides, communication
guidelines, mental health PDFs) using RAGAS + retrieval metrics.

Metrics : answer_relevancy, context_recall, context_precision (RAGAS)
          hit_at_k, MRR (retrieval, based on expected_category)

Usage:
  python ragas_doc_eval.py
  python ragas_doc_eval.py --sample 10 --debug
  python ragas_doc_eval.py --top-k 15 --generator-model gpt-4o
"""

import os
import sys
import json
import argparse
from tqdm import tqdm
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
import chromadb
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import AnswerRelevancy, ContextRecall, ContextPrecision
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from retrieval.bm25 import bm25_retrieve_docs, cid
from retrieval.reranker import rerank
from prompts.doc_answer_generator import _CATEGORY_SYSTEM, SYSTEM_PROMPT

load_dotenv()

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_FILE      = os.path.join(os.path.dirname(__file__), "test_questions_docs.json")
DOC_COLLECTION = "documents_collection1"
CHROMA_PATH    = os.path.join(PROJECT_ROOT, "rag", "vectorstore", "chroma_db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_MODEL  = "gpt-4o-mini"
TOP_CONTEXTS   = 6   # chunks passed to the generator

CATEGORY_MAP = {
    "alzheimers":    "alzheimers_and_other_sicknesses",
    "communication": "communication_guidelines",
    "mental_health": "mental_health",
    "general":       None,
}

# ── ARGUMENTS ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--top-k",           type=int, default=10)
parser.add_argument("--sample",          type=int, default=None,
                    help="Evaluate only first N questions.")
parser.add_argument("--category-filter", action="store_true", default=True)
parser.add_argument("--generator-model", type=str, default=DEFAULT_MODEL)
parser.add_argument("--ragas-judge",     type=str, default=DEFAULT_MODEL)
parser.add_argument("--debug",           action="store_true", default=False)
args = parser.parse_args()

# ── LOAD QUESTIONS ─────────────────────────────────────────────────────────────
with open(EVAL_FILE, encoding="utf-8") as f:
    questions = json.load(f)
if args.sample:
    questions = questions[:args.sample]

print(f"Loaded {len(questions)} questions | top_k={args.top_k} | model={args.generator_model}")

# ── CLIENTS ────────────────────────────────────────────────────────────────────
openai_client    = OpenAI(api_key=OPENAI_API_KEY)
ragas_llm        = ChatOpenAI(model=args.ragas_judge, api_key=OPENAI_API_KEY)
ragas_embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_collection(DOC_COLLECTION)
print(f"Collection '{DOC_COLLECTION}': {collection.count()} docs")


# ── EMBEDDINGS ─────────────────────────────────────────────────────────────────
_embed_cache: dict[str, list[float]] = {}

def precompute_embeddings(queries: list[str]) -> None:
    unique = [q for q in dict.fromkeys(queries) if q not in _embed_cache]
    if not unique:
        return
    print(f"Embedding {len(unique)} queries in one batch call...")
    for i in range(0, len(unique), 100):
        batch = unique[i : i + 100]
        resp  = openai_client.embeddings.create(input=batch, model="text-embedding-3-large")
        for q, obj in zip(batch, resp.data):
            _embed_cache[q] = obj.embedding

def embed(query: str) -> list[float]:
    if query not in _embed_cache:
        resp = openai_client.embeddings.create(input=[query], model="text-embedding-3-large")
        _embed_cache[query] = resp.data[0].embedding
    return _embed_cache[query]


# ── RRF MERGE ──────────────────────────────────────────────────────────────────
def rrf_merge(dense: list[tuple], sparse: list[tuple],
              top_k: int, k: int = 60) -> tuple[list, list]:
    scores:   dict[str, float] = {}
    registry: dict[str, tuple] = {}
    for rank, (doc, meta) in enumerate(dense):
        c = cid(doc)
        scores[c]   = scores.get(c, 0.0) + 1.0 / (k + rank + 1)
        registry[c] = (doc, meta)
    for rank, (doc, meta) in enumerate(sparse):
        c = cid(doc)
        scores[c]   = scores.get(c, 0.0) + 1.0 / (k + rank + 1)
        registry[c] = (doc, meta)
    top = sorted(scores, key=lambda c: scores[c], reverse=True)[:top_k]
    return [registry[c][0] for c in top], [registry[c][1] for c in top]


# ── CATEGORY DETECTION ─────────────────────────────────────────────────────────
def detect_category(query: str) -> str | None:
    try:
        resp = openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": _CATEGORY_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        return CATEGORY_MAP.get(resp.choices[0].message.content.strip().lower(), None)
    except Exception:
        return None


# ── RETRIEVAL ──────────────────────────────────────────────────────────────────
def retrieve(query: str, top_k: int) -> tuple[list[str], list[dict]]:
    category    = detect_category(query) if args.category_filter else None
    emb         = embed(query)
    effective_k = top_k + 3

    query_kwargs: dict = dict(
        query_embeddings=[emb],
        n_results=effective_k,
        include=["documents", "metadatas"],
    )
    if category:
        query_kwargs["where"] = {"category": {"$eq": category}}

    results     = collection.query(**query_kwargs)
    dense_docs  = results["documents"][0]
    dense_metas = results["metadatas"][0]

    # Fall back to unfiltered if category filter returned too few results
    if category and len(dense_docs) < top_k:
        results     = collection.query(
            query_embeddings=[emb],
            n_results=effective_k,
            include=["documents", "metadatas"],
        )
        dense_docs  = results["documents"][0]
        dense_metas = results["metadatas"][0]

    bm25_docs, bm25_metas = bm25_retrieve_docs(
        query, category, effective_k,
        collection_name=DOC_COLLECTION,
        chroma_path=CHROMA_PATH,
    )

    merged_docs, merged_metas = rrf_merge(
        list(zip(dense_docs, dense_metas)),
        list(zip(bm25_docs, bm25_metas)),
        effective_k,
    )
    return rerank(query, merged_docs, merged_metas, top_n=top_k)


# ── ANSWER GENERATION ──────────────────────────────────────────────────────────
def generate_answer(query: str, contexts: list[str]) -> str:
    resp = openai_client.chat.completions.create(
        model=args.generator_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{chr(10).join(contexts)}\n\nQuestion: {query}\n\nAnswer:"},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


# ── RETRIEVAL METRICS ──────────────────────────────────────────────────────────
def compute_retrieval(top_k: int) -> dict:
    hits, mrr = 0, 0.0
    for q in questions:
        expected = q.get("expected_category", "")
        _, metas = retrieve(q["query"], top_k)
        rank = next(
            (i + 1 for i, m in enumerate(metas)
             if m.get("category", "").lower() == expected.lower()),
            None,
        )
        if rank:
            hits += 1
            mrr  += 1 / rank
    total = len(questions)
    return {f"hit_at_{top_k}": hits / total, "mrr": mrr / total}


# ── BUILD RAGAS DATASET ────────────────────────────────────────────────────────
def build_dataset(top_k: int) -> Dataset:
    data = []
    print("Building dataset...")
    for q in tqdm(questions):
        contexts, _ = retrieve(q["query"], top_k)
        prompt_ctx  = contexts[:TOP_CONTEXTS]
        answer      = generate_answer(q["query"], prompt_ctx)

        if args.debug:
            print(f"\nQ: {q['query']}")
            print(f"  chunk: {contexts[0][:150] if contexts else '(empty)'}")
            print(f"  answer: {answer[:150]}")

        data.append({
            "question":     q["query"],
            "answer":       answer,
            "contexts":     prompt_ctx,
            "ground_truth": q["ground_truth"],
        })
    return Dataset.from_list(data)


# ── RUN RAGAS ──────────────────────────────────────────────────────────────────
def run_ragas(dataset: Dataset) -> dict:
    result = evaluate(
        dataset=dataset,
        metrics=[AnswerRelevancy(), ContextRecall(), ContextPrecision()],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        raise_exceptions=False,
    )
    df = dataset.to_pandas().join(result.to_pandas())

    if args.debug:
        print("\n── PER-QUESTION SCORES ──")
        for _, row in df.iterrows():
            print(f"\nQ:  {row['question'][:80]}")
            print(f"A:  {row['answer'][:120]}")
            print(f"AR: {row['answer_relevancy']:.3f}  |  CR: {row['context_recall']:.3f}  |  CP: {row['context_precision']:.3f}")

    return {
        "ragas_answer_relevancy": df["answer_relevancy"].mean(),
        "ragas_context_recall":   df["context_recall"].mean(),
        "ragas_context_precision": df["context_precision"].mean(),
    }


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    top_k = args.top_k

    precompute_embeddings([q["query"] for q in questions])

    print("Running retrieval metrics...")
    retrieval = compute_retrieval(top_k)

    dataset = build_dataset(top_k)

    print("Running RAGAS evaluation...")
    ragas = run_ragas(dataset)

    print("\n── RESULTS ──")
    for k, v in {**retrieval, **ragas}.items():
        print(f"{k}: {v:.4f}")
