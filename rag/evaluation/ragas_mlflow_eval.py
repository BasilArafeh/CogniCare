import os
import json
import argparse
from tqdm import tqdm
from dotenv import load_dotenv

import mlflow
from openai import OpenAI
import chromadb

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    answer_correctness,
    context_precision,
    context_recall,
)
from CogniCare.rag.pipeline.components.chunkers.chunker_medicines import MIN_TOKENS, MAX_TOKENS, OVERLAP_TOKENS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

# ── MLflow ─────────────────────────────────────────────
mlflow.set_tracking_uri("file:///Users/leensalman/Desktop/gp2/mlruns")

# ── CONFIG ─────────────────────────────────────────────
EVAL_FILE         = os.path.join(os.path.dirname(__file__), "test_questions.json")
CHROMA_PATH       = os.path.expanduser("/Users/leensalman/Desktop/gp2/CogniCare/rag/vectorstore/chroma_db")
OPENAI_COLLECTION = "medicines_openai8"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
MLFLOW_EXPERIMENT = "CogniCare-RAG-Evaluation"

# Medicines with many chunks need a larger effective_k to reliably surface
# the correct sub-topic chunk within top-k results.
HIGH_CHUNK_MEDICINES = {
    "warfarin", "diazepam", "alprazolam", "atorvastatin", "rivastigmine",
    "metformin", "bisoprolol", "perindopril", "donepezil",
}
HIGH_CHUNK_K_BOOST = 7   # effective_k = top_k + 7 for these medicines

# ── CHUNK TYPE MAP ─────────────────────────────────────
CHUNK_TYPE_MAP = {
    "side_effects":          ["side_effects"],
    "dosage":                ["dosage"],
    "interactions_overdose": ["interactions_and_overdose"],
    "storage":               ["storage"],
    "identity":              ["identity_and_usage"],
    "general":               None,
}

# FIX 4: For overdose/interaction queries, also include side_effects chunks as a
# secondary filter. OTC drugs (acetaminophen, ibuprofen, aspirin) store their
# overdose warnings inside the side_effects chunk, not interactions_and_overdose.
CHUNK_TYPE_MAP_IO_EXTENDED = ["interactions_and_overdose", "side_effects"]

# ── ARGUMENTS ──────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--top-k",         type=int,  default=6)   # FIX: raised from 3 → 6
parser.add_argument("--sample",        type=int,  default=None)
parser.add_argument("--run-name",      type=str,  default=None)
parser.add_argument("--query-rewrite", action="store_true", default=True)
parser.add_argument("--chunk-filter",  action="store_true", default=True)
parser.add_argument("--debug",         action="store_true", default=False,
                    help="Print per-question AR and answer for diagnosis")
args = parser.parse_args()

# ── LOAD QUESTIONS ─────────────────────────────────────
with open(EVAL_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

if args.sample:
    questions = questions[:args.sample]

print(f"Loaded {len(questions)} questions")

# ── CLIENTS ────────────────────────────────────────────
openai_client    = OpenAI(api_key=OPENAI_API_KEY)
ragas_llm        = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
ragas_embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)

# ── CHROMA ─────────────────────────────────────────────
client     = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(OPENAI_COLLECTION)

print(f"Loaded collection: {collection.count()} docs")

# ── EMBEDDING ──────────────────────────────────────────
def embed(query: str):
    return openai_client.embeddings.create(
        input=[query],
        model="text-embedding-3-large"
    ).data[0].embedding


# ── QUERY REWRITING ────────────────────────────────────
def rewrite_query(query: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical search assistant. "
                    "Rewrite the user's question as a short, precise English medical search query. "
                    "Include the medicine generic name if known, and the medical topic. "
                    "Output ONLY the rewritten query — no explanation, no punctuation at the end.\n\n"
                    "Examples:\n"
                    "Q: Can Exelon cause dizziness?\n"
                    "A: rivastigmine dizziness side effects\n\n"
                    "Q: Can Brufen be given every 4 hours?\n"
                    "A: ibuprofen dosage frequency\n\n"
                    "Q: What should be done if a patient overdoses on Panadol?\n"
                    "A: acetaminophen overdose treatment\n\n"
                    "Q: What drugs should not be taken with Coversyl?\n"
                    "A: perindopril drug interactions contraindications\n\n"
                    "Q: Is Crestor a cholesterol medication?\n"
                    "A: rosuvastatin indication usage\n\n"
                    "Q: What are the contraindications of Xanax in elderly patients?\n"
                    "A: alprazolam contraindications elderly\n\n"
                    "Q: Is Xanax safe for elderly patients with Alzheimer's?\n"
                    "A: alprazolam elderly safety contraindications\n\n"
                    "Q: Can Lipitor tablets be crushed?\n"
                    "A: atorvastatin tablet crushing administration"
                )
            },
            {"role": "user", "content": query}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()


# ── CHUNK TYPE DETECTION (LLM-based) ──────────────────
# FIX: Replace fragile keyword matching with a direct LLM classification call.
# The old keyword approach had a critical false-positive: "contraindications"
# contains the substring "indication", which matched the identity keyword list
# and routed those queries to identity_and_usage chunks instead of
# interactions_and_overdose. An LLM classifier handles natural language
# variation correctly, including "safe for elderly", "can it be crushed", etc.
_CLASSIFY_SYSTEM = """\
Classify this medical question into exactly one category. Output ONLY the category name.

Categories:
- side_effects      : questions about adverse effects, symptoms caused by the drug,
                      warnings, precautions, tolerability, safety profile
- dosage            : questions about dose, frequency, how to take, timing,
                      administration, how to apply a patch or cream
- interactions_overdose : questions about drug interactions, overdose, what happens if
                          too much is taken, contraindications, what NOT to take together,
                          safety in specific populations (elderly, pregnant, renal), 
                          whether a drug can be crushed or split
- identity          : questions about what a drug is used for, what condition it treats,
                      drug class, mechanism, what it is
- general           : anything else

Output one word only."""

def detect_chunk_types(query: str) -> list | None:
    """
    FIX: LLM-based classifier replacing keyword matching.
    Returns the chunk_type list to filter on, or None for unfiltered search.
    Falls back to None on any API error so retrieval is never blocked.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        category = response.choices[0].message.content.strip().lower()
    except Exception:
        return None  # safe fallback: unfiltered search

    # FIX 4: overdose/interaction queries also search side_effects because
    # OTC drugs store overdose info there.
    if category == "interactions_overdose":
        return CHUNK_TYPE_MAP_IO_EXTENDED

    return CHUNK_TYPE_MAP.get(category, None)


# ── MEDICINE NAME EXTRACTION ───────────────────────────
_EXTRACT_MEDICINE_SYSTEM = """\
Extract the medicine name from this question. Output ONLY the generic name in lowercase.
If you recognize the brand name, convert it to generic (e.g. Panadol → acetaminophen,
Brufen → ibuprofen, Aricept → donepezil, Exelon → rivastigmine, Concor → bisoprolol,
Lipitor → atorvastatin, Glucophage → metformin, Xanax → alprazolam, Valium → diazepam,
Crestor → rosuvastatin, Coversyl → perindopril, Ebixa → memantine, Reminyl → galantamine,
Zoloft → sertraline, Nexium → esomeprazole, Coumadin → warfarin).
If no medicine is mentioned, output: none"""

def extract_medicine_name(query: str) -> str | None:
    """
    FIX: Extract the target medicine name for metadata re-ranking.
    Returns lowercase generic name string or None.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _EXTRACT_MEDICINE_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        name = response.choices[0].message.content.strip().lower()
        return None if name == "none" else name
    except Exception:
        return None


# ── METADATA RE-RANKING ────────────────────────────────
def rerank_by_medicine(docs: list, metas: list, target_medicine: str | None, top_k: int):
    """
    FIX: Boost chunks whose generic_name or brand_names metadata matches the
    detected medicine. This ensures the correct medicine is always ranked first
    when multiple medicines appear in the top results.

    Strategy: move matching chunks to the front, preserve relative order within
    each group, then truncate to top_k.
    """
    if not target_medicine:
        return docs[:top_k], metas[:top_k]

    matching, non_matching = [], []
    for doc, meta in zip(docs, metas):
        generic    = meta.get("generic_name", "").lower()
        brands_raw = meta.get("brand_names", "")
        brands     = [b.strip().lower() for b in brands_raw.split(",") if b.strip()]

        if target_medicine == generic or target_medicine in brands:
            matching.append((doc, meta))
        else:
            non_matching.append((doc, meta))

    reranked = matching + non_matching
    reranked_docs  = [d for d, _ in reranked]
    reranked_metas = [m for _, m in reranked]
    return reranked_docs[:top_k], reranked_metas[:top_k]


# ── RETRIEVAL ──────────────────────────────────────────
def retrieve(query: str, top_k: int, use_filter: bool = True, use_rewrite: bool = True):
    search_query    = rewrite_query(query) if use_rewrite else query
    emb             = embed(search_query)
    chunk_types     = detect_chunk_types(query) if use_filter else None
    target_medicine = extract_medicine_name(query)

    # FIX: larger effective_k for high-chunk medicines
    if target_medicine and target_medicine in HIGH_CHUNK_MEDICINES:
        effective_k = top_k + HIGH_CHUNK_K_BOOST
    else:
        effective_k = top_k + 2 if chunk_types else top_k

    query_kwargs = dict(
        query_embeddings=[emb],
        n_results=effective_k,
        include=["documents", "metadatas"],
    )

    if chunk_types:
        query_kwargs["where"] = {"chunk_type": {"$in": chunk_types}}

    results = collection.query(**query_kwargs)
    docs    = results["documents"][0]
    metas   = results["metadatas"][0]

    # Soft fallback: too few filtered results → retry without filter
    if chunk_types and len(docs) < top_k:
        fallback = dict(
            query_embeddings=[emb],
            n_results=effective_k,
            include=["documents", "metadatas"],
        )
        results = collection.query(**fallback)
        docs    = results["documents"][0]
        metas   = results["metadatas"][0]

    # FIX: medicine-aware re-ranking before final truncation
    docs, metas = rerank_by_medicine(docs, metas, target_medicine, top_k)

    return docs, metas


# ── SYSTEM PROMPT ──────────────────────────────────────
SYSTEM_PROMPT = """\
You are a medical assistant. Your ONLY source of information is the context provided below.

Strict rules — follow every one:
1. Answer using ONLY facts stated explicitly in the context. Do not add anything else.
2. Do NOT use your general medical knowledge under any circumstances.
3. Always answer in English.
4. When the context mentions a brand name for the medicine, include it in your answer
   in the format "BrandName (generic_name)" — e.g. "Panadol (acetaminophen)".
   If only the generic name is in the context, use only that.
5. Open your answer by directly addressing the specific topic of the question using the
   medicine name — e.g. if asked about side effects of Exelon, begin with
   "Exelon (rivastigmine) can cause..." not "This medication can cause...".
6. Keep your answer to 2–5 sentences. Be direct and complete — cover all relevant details.
7. Do not start with "Based on the context..." or "According to the provided information...".
8. If the context does not contain the answer, respond only with: "This information is not available in the provided context."
9. Do not add safety warnings, recommendations, or advice beyond what is explicitly stated in the context.\
"""

def generate_answer(query: str, contexts: list) -> str:
    context_block = "\n\n---\n\n".join(contexts)

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
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
        temperature=0
    )
    return response.choices[0].message.content.strip()


# ── IS_CORRECT ─────────────────────────────────────────
def is_correct(meta, expected):
    gen        = meta.get("generic_name", "").lower()
    brands_raw = meta.get("brand_names", "")

    if isinstance(brands_raw, str):
        brands = [b.strip().lower() for b in brands_raw.split(",") if b.strip()]
    else:
        brands = [b.lower() for b in brands_raw]

    exp = expected.lower()
    if exp == gen:
        return True
    for b in brands:
        if exp == b:
            return True
    return False


# ── RETRIEVAL METRICS ──────────────────────────────────
def compute_retrieval(top_k):
    hits, mrr = 0, 0

    for q in questions:
        _, metas = retrieve(q["query"], top_k, args.chunk_filter, args.query_rewrite)
        rank = None

        for i, m in enumerate(metas):
            if is_correct(m, q["expected_generic"]):
                rank = i + 1
                break

        if rank:
            hits += 1
            mrr += 1 / rank

    total = len(questions)
    return {
        f"hit_at_{top_k}": hits / total,
        "mrr":              mrr / total,
    }


# ── BUILD RAGAS DATASET ────────────────────────────────
def build_dataset(top_k):
    data = []
    print("Building dataset...")

    for q in tqdm(questions):
        contexts, _ = retrieve(q["query"], top_k, args.chunk_filter, args.query_rewrite)

        if args.debug:
            print(f"\nQUESTION: {q['query']}")
            print(f"TOP CHUNK: {contexts[0][:200]}")

        answer = generate_answer(q["query"], contexts)

        data.append({
            "question":     q["query"],
            "answer":       answer,
            "contexts":     contexts,
            "ground_truth": q.get("ground_truth", q["expected_generic"]),
        })

    return Dataset.from_list(data)


# ── RUN RAGAS ──────────────────────────────────────────
def run_ragas(dataset):
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            answer_correctness,
            context_precision,
            context_recall,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        raise_exceptions=False
    )

    df_scores = result.to_pandas()
    df_input  = dataset.to_pandas()

    df = df_input.join(df_scores)

    if args.debug:
        print("\n── PER-QUESTION SCORES ──")
        for _, row in df.iterrows():
            print(f"\nQ:   {row['question'][:80]}")
            print(f"A:   {row['answer'][:120]}")
            print(f"AR:  {row['answer_relevancy']:.3f}  |  F: {row['faithfulness']:.3f}")

    return {
        "ragas_faithfulness":       df["faithfulness"].mean(),
        "ragas_answer_relevancy":   df["answer_relevancy"].mean(),
        "ragas_answer_correctness": df["answer_correctness"].mean(),
        "ragas_context_precision":  df["context_precision"].mean(),
        "ragas_context_recall":     df["context_recall"].mean(),
    }


# ── MAIN ───────────────────────────────────────────────
if __name__ == "__main__":
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    top_k = args.top_k

    print("Running retrieval...")
    retrieval = compute_retrieval(top_k)

    dataset = build_dataset(top_k)

    print("Running RAGAS...")
    ragas = run_ragas(dataset)

    metrics = {**retrieval, **ragas}

    print("\nRESULTS")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

    with mlflow.start_run(run_name=args.run_name or f"run_top{top_k}"):
        mlflow.log_params({
            "top_k":                top_k,
            "min_tokens":           MIN_TOKENS,
            "max_tokens":           MAX_TOKENS,
            "overlap_tokens":       OVERLAP_TOKENS,
            "embedding_model":      "text-embedding-3-large",
            "llm_model":            "gpt-4o-mini",
            "query_rewrite":        args.query_rewrite,
            "chunk_filter":         args.chunk_filter,
            "chunk_classifier":     "llm_gpt4o_mini",
            "medicine_reranking":   True,
            "io_dual_type_search":  True,
            "high_chunk_k_boost":   HIGH_CHUNK_K_BOOST,
            "test_set":             "english_direct_v3",
        })
        mlflow.log_metrics(metrics)

    print("\n✅ Logged to MLflow")