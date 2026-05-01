"""
ragas_doc_eval.py  —  CogniCare Document RAG Evaluation
=========================================================

Evaluates the documents pipeline (Alzheimer's guides, communication
guidelines, mental health PDFs) using RAGAS + MLflow.

Collection : documents_collection (ChromaDB)
             Contains ALL three document categories:
               - alzheimers_and_other_sicknesses
               - communication_guidelines
               - mental_health
             Distinguished by the `category` metadata field.

Retrieval  : Hybrid — dense (text-embedding-3-large) + full-corpus BM25,
             merged with RRF, then reranked by BGE (bge-reranker-v2-m3).

Metrics    : faithfulness, answer_relevancy, context_recall (RAGAS)
             hit_at_k, MRR (retrieval, based on expected_category)

Cost estimate per 70 questions (approximate):
  ~$0.15–0.25  (gpt-4o-mini gen + gpt-4o-mini RAGAS judge)

Usage:
  python ragas_doc_eval.py
  python ragas_doc_eval.py --sample 10 --debug
  python ragas_doc_eval.py --generator-model gpt-4o --ragas-judge gpt-4o
"""

import os
import sys
import json
import argparse
from functools import lru_cache
from tqdm import tqdm
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mlflow
from openai import OpenAI
import chromadb

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from retrieval.bm25 import bm25_retrieve_docs, cid
from retrieval.reranker import rerank

load_dotenv()

# ── MLflow ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

mlflow.set_tracking_uri("file://" + os.path.join(PROJECT_ROOT, "mlruns"))

CHROMA_PATH = os.path.join(PROJECT_ROOT, "rag", "vectorstore", "chroma_db")
# ── CONFIG ─────────────────────────────────────────────────────────────────────
EVAL_FILE         = os.path.join(os.path.dirname(__file__), "test_questions_docs.json")
DOC_COLLECTION    = "documents_collection1"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
MLFLOW_EXPERIMENT = "CogniCare-Doc-RAG-Evaluation"

# ── MODELS ─────────────────────────────────────────────────────────────────────
GENERATOR_MODEL   = "gpt-4o-mini"
UTILITY_MODEL     = "gpt-4o-mini"
RAGAS_JUDGE_MODEL = "gpt-4o-mini"

# ── RETRIEVAL CONFIG ───────────────────────────────────────────────────────────
GEN_K_EASY = 4
GEN_K_HARD = 6

# ── CATEGORY MAP ───────────────────────────────────────────────────────────────
# Maps LLM-detected topic label → ChromaDB metadata category value.
# None means no category filter (search across all documents).
CATEGORY_MAP = {
    "alzheimers":   "alzheimers_and_other_sicknesses",
    "communication": "communication_guidelines",
    "mental_health": "mental_health",
    "general":       None,
}

# ── ARGUMENTS ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--top-k",           type=int,  default=10)
parser.add_argument("--sample",          type=int,  default=None,
                    help="Evaluate only first N questions (cheap iteration).")
parser.add_argument("--run-name",        type=str,  default=None)
parser.add_argument("--query-rewrite",   action="store_true", default=True)
parser.add_argument("--category-filter", action="store_true", default=True,
                    help="Filter ChromaDB and BM25 by detected category.")
parser.add_argument("--full-ragas",      action="store_true", default=False,
                    help="Add context_precision metric (expensive).")
parser.add_argument("--generator-model", type=str,  default=GENERATOR_MODEL)
parser.add_argument("--ragas-judge",     type=str,  default=RAGAS_JUDGE_MODEL)
parser.add_argument("--debug",           action="store_true", default=False)
args = parser.parse_args()

GENERATOR_MODEL   = args.generator_model
RAGAS_JUDGE_MODEL = args.ragas_judge

# ── LOAD QUESTIONS ─────────────────────────────────────────────────────────────
with open(EVAL_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

if args.sample:
    questions = questions[:args.sample]

print(f"Loaded {len(questions)} questions")
print(f"Generator: {GENERATOR_MODEL} | RAGAS judge: {RAGAS_JUDGE_MODEL} | "
      f"Category filter: {args.category_filter} | Full RAGAS: {args.full_ragas}")

# ── CLIENTS ────────────────────────────────────────────────────────────────────
openai_client    = OpenAI(api_key=OPENAI_API_KEY)
ragas_llm        = ChatOpenAI(model=RAGAS_JUDGE_MODEL, api_key=OPENAI_API_KEY)
ragas_embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)

# ── CHROMA ─────────────────────────────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_collection(DOC_COLLECTION)
print(f"Loaded collection '{DOC_COLLECTION}': {collection.count()} docs")


# ── EMBEDDING (cached) ─────────────────────────────────────────────────────────
@lru_cache(maxsize=512)
def embed(query: str) -> list[float]:
    return openai_client.embeddings.create(
        input=[query],
        model="text-embedding-3-large"
    ).data[0].embedding


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

    top_cids  = sorted(scores, key=lambda c: scores[c], reverse=True)[:top_k]
    out_docs  = [registry[c][0] for c in top_cids]
    out_metas = [registry[c][1] for c in top_cids]
    return out_docs, out_metas


# ── QUERY REWRITING ────────────────────────────────────────────────────────────
def rewrite_query(query: str) -> str:
    response = openai_client.chat.completions.create(
        model=UTILITY_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinical search assistant specialising in dementia, "
                    "Alzheimer's disease, and caregiver communication. "
                    "Rewrite the user's question as a short, precise English search query "
                    "that will retrieve the most relevant passages from clinical guidelines "
                    "and patient education documents. "
                    "Include key clinical terms. "
                    "Output ONLY the rewritten query — no explanation.\n\n"
                    "Examples:\n"
                    "Q: What are the early signs of Alzheimer's?\n"
                    "A: early symptoms signs Alzheimer's disease mild cognitive impairment\n\n"
                    "Q: How should a caregiver talk to someone with dementia?\n"
                    "A: communication strategies dementia caregiver verbal non-verbal\n\n"
                    "Q: What is caregiver burnout?\n"
                    "A: caregiver burnout stress exhaustion dementia carer wellbeing\n\n"
                    "Q: How does Lewy body dementia differ from Alzheimer's?\n"
                    "A: Lewy body dementia vs Alzheimer's differences symptoms comparison\n\n"
                    "Q: Can depression occur in Alzheimer's patients?\n"
                    "A: depression Alzheimer's dementia psychiatric symptoms mood\n\n"
                    "Q: How does dementia progress from mild to severe?\n"
                    "A: dementia stages progression mild moderate severe decline"
                )
            },
            {"role": "user", "content": query}
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


# ── CATEGORY DETECTION ─────────────────────────────────────────────────────────
_CATEGORY_SYSTEM = """\
Classify this question into exactly one category. Output ONLY the category name.

Categories:
- alzheimers   : questions about Alzheimer's disease, dementia types (vascular, Lewy body,
                 frontotemporal, mixed), dementia stages, symptoms, diagnosis, progression,
                 risk factors, genetics, cognitive stimulation, music therapy, nutrition
- communication: questions about how to communicate with dementia patients, caregiver
                 communication strategies, person-centred care, validation therapy,
                 managing difficult behaviours, daily care activities, reminiscence,
                 dementia-friendly environments
- mental_health: questions about caregiver mental health, caregiver burnout, stress,
                 depression or anxiety in caregivers or patients, psychological wellbeing,
                 grief, guilt, coping strategies, support groups, respite care,
                 family conflict, cultural aspects of caregiving
- general      : any other topic

Output one word only."""

def detect_category(query: str) -> str | None:
    try:
        response = openai_client.chat.completions.create(
            model=UTILITY_MODEL,
            messages=[
                {"role": "system", "content": _CATEGORY_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        cat = response.choices[0].message.content.strip().lower()
        return CATEGORY_MAP.get(cat, None)
    except Exception:
        return None


# ── RETRIEVAL ──────────────────────────────────────────────────────────────────
def retrieve(query: str, top_k: int,
             use_rewrite: bool = True, use_filter: bool = True,
             difficulty: str = "easy") -> tuple[list[str], list[dict]]:

    search_query = rewrite_query(query) if use_rewrite else query
    category     = detect_category(query) if use_filter else None

    emb = embed(search_query)

    # Retrieve extra candidates before reranking
    effective_k = top_k + 5 if difficulty == "hard" else top_k + 3

    # ── Dense retrieval ────────────────────────────────────────────────────────
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

    # Fall back to unfiltered dense search if category filter returned too few
    if category and len(dense_docs) < top_k:
        results     = collection.query(
            query_embeddings=[emb],
            n_results=effective_k,
            include=["documents", "metadatas"],
        )
        dense_docs  = results["documents"][0]
        dense_metas = results["metadatas"][0]

    # ── BM25 retrieval ─────────────────────────────────────────────────────────
    bm25_docs, bm25_metas = bm25_retrieve_docs(
        search_query, category, effective_k,
        collection_name=DOC_COLLECTION,
        chroma_path=CHROMA_PATH,
    )

    # ── RRF merge ──────────────────────────────────────────────────────────────
    dense_pairs  = list(zip(dense_docs, dense_metas))
    sparse_pairs = list(zip(bm25_docs, bm25_metas))
    merged_docs, merged_metas = rrf_merge(dense_pairs, sparse_pairs, effective_k)

    # ── BGE reranker ───────────────────────────────────────────────────────────
    merged_docs, merged_metas = rerank(search_query, merged_docs, merged_metas, top_n=top_k)

    return merged_docs, merged_metas


# ── SYSTEM PROMPT ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a clinical assistant specialising in dementia and Alzheimer's disease care.
Answer the question using ONLY the context provided below.

Rules:
1. Use ONLY facts stated verbatim or clearly implied in the context.
   Do not add clinical knowledge, inferences, or conclusions not in the context.
2. Always answer in English.
3. For yes/no questions, begin with "Yes" or "No" followed by a brief explanation.
4. Otherwise, answer directly and concisely.
5. 1–2 sentences for simple questions. 2–4 sentences for complex ones.
6. Do not start with "Based on the context" or "According to the information provided".
7. If the context only partially answers the question, state what it does say and stop.
   Never write sentences about what the context does not contain or does not specify.
8. Do not add advisory language such as "it is recommended", "always consult a doctor",
   or "caution is advised" unless explicitly stated in the context.
9. Never draw conclusions or make inferences beyond what the context explicitly states."""


def generate_answer(query: str, contexts: list[str]) -> str:
    context_block = "\n\n---\n\n".join(contexts)
    response = openai_client.chat.completions.create(
        model=GENERATOR_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context_block}\n\n"
                    f"Question: {query}\n\n"
                    "Answer:"
                )
            }
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


# ── RETRIEVAL METRIC ───────────────────────────────────────────────────────────
def compute_retrieval(top_k: int) -> dict:
    """
    Hit-rate: does any top-K chunk come from the expected category?
    MRR: reciprocal rank of the first chunk from the expected category.
    """
    hits, mrr = 0, 0.0
    for q in questions:
        expected_cat = q.get("expected_category", "")
        difficulty   = q.get("difficulty", "easy")
        _, metas = retrieve(q["query"], top_k, args.query_rewrite,
                            args.category_filter, difficulty=difficulty)
        rank = next(
            (i + 1 for i, m in enumerate(metas)
             if m.get("category", "").lower() == expected_cat.lower()),
            None
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
        difficulty = q.get("difficulty", "easy")
        contexts, _ = retrieve(
            q["query"], top_k, args.query_rewrite,
            args.category_filter, difficulty=difficulty
        )

        gen_k           = GEN_K_EASY if difficulty == "easy" else GEN_K_HARD
        prompt_contexts = contexts[:gen_k]

        answer = generate_answer(q["query"], prompt_contexts)

        if args.debug:
            print(f"\nQUESTION [{difficulty}]: {q['query']}")
            print(f"TOP CHUNK:  {contexts[0][:200] if contexts else '(empty)'}")
            print(f"ANSWER:     {answer[:200]}")

        data.append({
            "question":     q["query"],
            "answer":       answer,
            "contexts":     prompt_contexts,
            "ground_truth": q["ground_truth"],
        })

    return Dataset.from_list(data)


# ── RUN RAGAS ──────────────────────────────────────────────────────────────────
def run_ragas(dataset: Dataset) -> dict:
    metrics_list = [Faithfulness(), AnswerRelevancy(), ContextRecall()]
    if args.full_ragas:
        from ragas.metrics import ContextPrecision
        metrics_list.append(ContextPrecision())
        print("Full RAGAS: context_precision enabled")

    result = evaluate(
        dataset=dataset,
        metrics=metrics_list,
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        raise_exceptions=False,
    )

    df_scores = result.to_pandas()
    df_input  = dataset.to_pandas()
    df        = df_input.join(df_scores)

    if args.debug:
        print("\n── PER-QUESTION SCORES ──")
        for _, row in df.iterrows():
            cp_str = f"  |  CP: {row['context_precision']:.3f}" if args.full_ragas else ""
            print(f"\nQ:  {row['question'][:80]}")
            print(f"A:  {row['answer'][:120]}")
            print(f"F:  {row['faithfulness']:.3f}  |  AR: {row['answer_relevancy']:.3f}"
                  f"  |  CR: {row['context_recall']:.3f}{cp_str}")

    out = {
        "ragas_faithfulness":     df["faithfulness"].mean(),
        "ragas_answer_relevancy": df["answer_relevancy"].mean(),
        "ragas_context_recall":   df["context_recall"].mean(),
    }
    if args.full_ragas:
        out["ragas_context_precision"] = df["context_precision"].mean()
    return out


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    top_k = args.top_k

    print("Running retrieval metrics...")
    retrieval = compute_retrieval(top_k)

    dataset = build_dataset(top_k)

    print("Running RAGAS evaluation...")
    ragas = run_ragas(dataset)

    metrics = {**retrieval, **ragas}

    print("\n── RESULTS ──")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

    with mlflow.start_run(run_name=args.run_name or f"doc_run_top{top_k}"):
        mlflow.log_params({
            "top_k":              top_k,
            "generator_model":    GENERATOR_MODEL,
            "utility_model":      UTILITY_MODEL,
            "ragas_judge_model":  RAGAS_JUDGE_MODEL,
            "embedding_model":    "text-embedding-3-large",
            "query_rewrite":      args.query_rewrite,
            "category_filter":    args.category_filter,
            "gen_k_easy":         GEN_K_EASY,
            "gen_k_hard":         GEN_K_HARD,
            "hybrid_search":      True,
            "bge_reranker":       True,
            "full_ragas":         args.full_ragas,
            "embedding_cache":    True,
            "test_set":           "doc_eval_v1",
            "chunk_collection":   DOC_COLLECTION,
            "pipeline":           "documents",
        })
        mlflow.log_metrics(metrics)

    print("\n✅ Logged to MLflow")
