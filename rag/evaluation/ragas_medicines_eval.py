"""
ragas_mlflow_eval_cheap.py  —  CogniCare RAG Evaluation (Cost-Optimised)
=========================================================================

Cost reductions vs. original
------------------------------
1.  Generator: gpt-4o  →  gpt-4o-mini
    Biggest single saving. gpt-4o-mini is ~15x cheaper per token.
    For a closed-context medical RAG with a tight system prompt the
    quality drop is small — the retrieval does the heavy lifting.

2.  Faithfulness guardrail DISABLED by default (--no-guardrail is now True)
    The guardrail was a second full gpt-4o generation call per question.
    Removing it halves generation cost. Re-enable with --guardrail flag
    if faithfulness scores are too low.

3.  RAGAS judge: gpt-4o  →  gpt-4o-mini
    RAGAS makes many small judge calls per question.  gpt-4o-mini is
    accurate enough for faithfulness/AR on factual medical text.
    Switch back with --ragas-judge gpt-4o for a final "gold" run.

4.  Utility calls (rewrite, classify, extract): already gpt-4o-mini — kept.

5.  RAGAS metrics trimmed: context_precision removed.
    context_precision is expensive (one LLM call per retrieved chunk)
    and least actionable during development. Keep faithfulness +
    answer_relevancy + context_recall as the core triad.
    Re-enable with --full-ragas flag.

6.  --sample default suggestion: pass --sample 20 for quick iteration.
    Full eval only needed for final reporting.

7.  Embedding model kept as text-embedding-3-large — switching to
    text-embedding-3-small would save ~5x on embedding cost but would
    require rebuilding the ChromaDB collection, so left unchanged.

Cost estimate per 100 questions (approximate):
  Original:  ~$3–5   (gpt-4o gen×2 + gpt-4o RAGAS judge)
  This file: ~$0.20–0.40  (gpt-4o-mini gen×1 + gpt-4o-mini RAGAS judge)
"""

import os
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from medicines.chunk import MIN_TOKENS, MAX_TOKENS, OVERLAP_TOKENS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from retrieval.bm25 import bm25_retrieve, cid
from retrieval.reranker import rerank

load_dotenv()

# ── MLflow ─────────────────────────────────────────────────────────────────────
mlflow.set_tracking_uri("file:///content/drive/MyDrive/cognigp2v2/gp2/mlruns")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
EVAL_FILE         = os.path.join(os.path.dirname(__file__), "test_questions.json")
CHROMA_PATH       = "/content/drive/MyDrive/cognigp2v2/gp2/CogniCare/rag/vectorstore/chroma_db"
OPENAI_COLLECTION = "medicines_openai15"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
MLFLOW_EXPERIMENT = "CogniCare-RAG-Evaluation"

# ── MODELS ─────────────────────────────────────────────────────────────────────
# COST CUT 1: gpt-4o → gpt-4o-mini for generation (~15x cheaper per token).
# The tight system prompt + retrieved context keeps quality high enough for eval.
# Switch back to "gpt-4o" only for a final "gold standard" run.
GENERATOR_MODEL  = "gpt-4o-mini"

# Utility calls: already cheap, unchanged.
UTILITY_MODEL    = "gpt-4o-mini"

# COST CUT 3: gpt-4o → gpt-4o-mini for RAGAS judge.
# gpt-4o-mini scores reliably for factual medical text; gpt-4o only needed
# for nuanced generation quality judgement on a final run.
RAGAS_JUDGE_MODEL = "gpt-4o-mini"

HIGH_CHUNK_MEDICINES = {
    "sertraline", "fluoxetine", "lisinopril", "haloperidol", "carbamazepine",
    "diazepam", "warfarin", "digoxin", "furosemide", "lorazepam",
    "atorvastatin", "metformin", "alprazolam", "rivastigmine",
    "insulin glargine", "donepezil", "bisoprolol",
}
HIGH_CHUNK_K_BOOST = 13

# ── CHUNK TYPE MAP ─────────────────────────────────────────────────────────────
CHUNK_TYPE_MAP = {
    "side_effects":          ["side_effects", "special_populations"],
    "dosage":                ["dosage", "administration"],
    "administration":        ["administration", "dosage"],
    "interactions_overdose": ["interactions_and_overdose"],
    "storage":               ["storage"],
    "identity":              ["identity_and_usage"],
    "general":               None,
}
# OTC drugs store overdose info inside side_effects, so search both
CHUNK_TYPE_MAP_IO_EXTENDED = ["interactions_and_overdose", "side_effects", "special_populations"]

GEN_K_EASY = 4
GEN_K_HARD = 6

# ── ARGUMENTS ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--top-k",         type=int,  default=15)
parser.add_argument("--sample",        type=int,  default=None,
                    help="Evaluate only first N questions. Use --sample 20 for cheap iteration.")
parser.add_argument("--run-name",      type=str,  default=None)
parser.add_argument("--query-rewrite", action="store_true", default=True)
parser.add_argument("--chunk-filter",  action="store_true", default=True)

# COST CUT 2: guardrail OFF by default. Was True (expensive second gpt-4o call).
# Re-enable with --guardrail when you need maximum faithfulness signal.
parser.add_argument("--guardrail",     action="store_true", default=False,
                    help="Enable faithfulness guardrail (adds one LLM call per question)")

# COST CUT 5: full RAGAS metrics OFF by default (context_precision is expensive).
# Re-enable with --full-ragas for a final reporting run.
parser.add_argument("--full-ragas",    action="store_true", default=False,
                    help="Add context_precision metric (expensive: one LLM call per chunk)")

# Override model flags — lets you do a cheap dev run then a gold run without
# editing the file.
parser.add_argument("--generator-model", type=str, default=GENERATOR_MODEL,
                    help="Override generator model (e.g. gpt-4o for a gold run)")
parser.add_argument("--ragas-judge",     type=str, default=RAGAS_JUDGE_MODEL,
                    help="Override RAGAS judge model (e.g. gpt-4o for a gold run)")

parser.add_argument("--debug",         action="store_true", default=False)
args = parser.parse_args()

# Apply overrides
GENERATOR_MODEL   = args.generator_model
RAGAS_JUDGE_MODEL = args.ragas_judge

# ── LOAD QUESTIONS ─────────────────────────────────────────────────────────────
with open(EVAL_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

if args.sample:
    questions = questions[:args.sample]

print(f"Loaded {len(questions)} questions")
print(f"Generator: {GENERATOR_MODEL} | RAGAS judge: {RAGAS_JUDGE_MODEL} | "
      f"Guardrail: {args.guardrail} | Full RAGAS: {args.full_ragas}")

# ── CLIENTS ────────────────────────────────────────────────────────────────────
openai_client    = OpenAI(api_key=OPENAI_API_KEY)
ragas_llm        = ChatOpenAI(model=RAGAS_JUDGE_MODEL, api_key=OPENAI_API_KEY)
ragas_embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)

# ── CHROMA ─────────────────────────────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_collection(OPENAI_COLLECTION)
print(f"Loaded collection: {collection.count()} docs")


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
    scores: dict[str, float] = {}
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


# ── CHUNK TYPE DETECTION ───────────────────────────────────────────────────────
_CLASSIFY_SYSTEM = """\
Classify this medical question into exactly one category. Output ONLY the category name.

Categories:
- side_effects      : questions about adverse effects, symptoms caused by the drug,
                      warnings, precautions, tolerability, safety profile
- dosage            : questions about dose, frequency, how to take, timing
- administration    : questions about how to apply a patch, cream, or injection, or how to use a device
- interactions_overdose : questions about drug interactions, overdose, what happens if
                          too much is taken, contraindications, what NOT to take together,
                          safety in specific populations (elderly, pregnant, renal),
                          whether a drug can be crushed or split
- identity          : questions about what a drug is used for, what condition it treats,
                      drug class, mechanism, what it is
- general           : anything else

Output one word only."""

def detect_chunk_types(query: str) -> list | None:
    try:
        response = openai_client.chat.completions.create(
            model=UTILITY_MODEL,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        category = response.choices[0].message.content.strip().lower()
    except Exception:
        return None

    if category == "interactions_overdose":
        return CHUNK_TYPE_MAP_IO_EXTENDED

    return CHUNK_TYPE_MAP.get(category, None)


# ── MEDICINE NAME EXTRACTION ───────────────────────────────────────────────────
_BRAND_MAP = (
    "Panadol → acetaminophen, Brufen → ibuprofen, Aricept → donepezil, "
    "Exelon → rivastigmine, Ebixa → memantine, Reminyl → galantamine, "
    "Concor → bisoprolol, Lipitor → atorvastatin, Glucophage → metformin, "
    "Xanax → alprazolam, Valium → diazepam, Crestor → rosuvastatin, "
    "Zoloft → sertraline, Nexium → esomeprazole, Coumadin → warfarin, "
    "Lantus → insulin glargine, Sinemet → levodopa carbidopa, "
    "Tegretol → carbamazepine, Prozac → fluoxetine, Haldol → haloperidol, "
    "Lasix → furosemide, Ativan → lorazepam, Plavix → clopidogrel"
)

_EXTRACT_MEDICINE_SYSTEM = f"""\
Extract the medicine name from this question. Output ONLY the generic name in lowercase.
Convert brand names to generic where known ({_BRAND_MAP}).
If no medicine is mentioned, output: none"""

def extract_medicine_name(query: str) -> str | None:
    try:
        response = openai_client.chat.completions.create(
            model=UTILITY_MODEL,
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


# ── MULTI-DRUG NAME EXTRACTION ─────────────────────────────────────────────────
_EXTRACT_ALL_MEDICINES_SYSTEM = f"""\
Extract ALL medicine names mentioned in this question.
Output ONLY lowercase generic names, one per line.
Convert brand names to generic where known ({_BRAND_MAP}).
If no medicine is mentioned, output: none"""

def extract_all_medicine_names(query: str) -> list[str]:
    try:
        response = openai_client.chat.completions.create(
            model=UTILITY_MODEL,
            messages=[
                {"role": "system", "content": _EXTRACT_ALL_MEDICINES_SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=60,
        )
        text = response.choices[0].message.content.strip().lower()
        return [n.strip() for n in text.splitlines()
                if n.strip() and n.strip() != "none"]
    except Exception:
        return []


# ── PARALLEL QUERY PREPROCESSING ──────────────────────────────────────────────
def preprocess_query(query: str, use_rewrite: bool, use_filter: bool, difficulty: str):
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_rewrite = ex.submit(rewrite_query, query) if use_rewrite else None
        f_chunk   = ex.submit(detect_chunk_types, query) if use_filter else None

        if difficulty == "hard":
            f_meds = ex.submit(extract_all_medicine_names, query)
        else:
            f_meds = ex.submit(extract_medicine_name, query)

        search_query  = f_rewrite.result() if f_rewrite else query
        chunk_types   = f_chunk.result()   if f_chunk   else None
        meds_result   = f_meds.result()

    if difficulty == "hard":
        all_medicines   = meds_result if isinstance(meds_result, list) else []
        target_medicine = all_medicines[0] if len(all_medicines) == 1 else None
    else:
        all_medicines   = []
        target_medicine = meds_result if isinstance(meds_result, str) else None

    return search_query, chunk_types, target_medicine, all_medicines


# ── METADATA RE-RANKING ────────────────────────────────────────────────────────
def rerank_by_medicine(docs: list, metas: list, target_medicine: str | None, top_k: int):
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

    reranked       = matching + non_matching
    reranked_docs  = [d for d, _ in reranked]
    reranked_metas = [m for _, m in reranked]
    return reranked_docs[:top_k], reranked_metas[:top_k]


# ── BM25 WRAPPER ───────────────────────────────────────────────────────────────
def _bm25_retrieve(query: str, generic_name: str | None,
                   chunk_types: list | None, n: int) -> tuple[list, list]:
    return bm25_retrieve(
        query, generic_name, chunk_types, n,
        collection_name=OPENAI_COLLECTION,
        chroma_path=CHROMA_PATH,
    )


# ── MULTI-DRUG RETRIEVAL ───────────────────────────────────────────────────────
def _retrieve_multi_drug(emb, search_query: str, medicines: list[str],
                         chunk_types, top_k: int):
    per_drug_k   = max(5, -(-top_k // len(medicines)))
    drug_buckets: list[list] = []
    seen: set = set()

    for med in medicines:
        dense_pairs: list[tuple] = []
        where_filter: dict = {"generic_name": {"$eq": med}}
        if chunk_types:
            where_filter = {"$and": [
                {"generic_name": {"$eq": med}},
                {"chunk_type":   {"$in": chunk_types}},
            ]}
        try:
            res = collection.query(
                query_embeddings=[emb],
                n_results=per_drug_k,
                where=where_filter,
                include=["documents", "metadatas"],
            )
            dense_pairs = list(zip(res["documents"][0], res["metadatas"][0]))
        except Exception:
            pass

        bm25_docs, bm25_metas = _bm25_retrieve(search_query, med, chunk_types, per_drug_k)
        sparse_pairs = list(zip(bm25_docs, bm25_metas))

        merged_docs, merged_metas = rrf_merge(dense_pairs, sparse_pairs, per_drug_k)
        bucket: list = []
        for doc, meta in zip(merged_docs, merged_metas):
            if doc not in seen:
                seen.add(doc)
                bucket.append((doc, meta))
        drug_buckets.append(bucket)

    all_pairs: list = []
    max_len = max((len(b) for b in drug_buckets), default=0)
    for i in range(max_len):
        for bucket in drug_buckets:
            if i < len(bucket):
                all_pairs.append(bucket[i])

    all_docs  = [d for d, _ in all_pairs]
    all_metas = [m for _, m in all_pairs]

    if len(all_docs) < top_k:
        res = collection.query(
            query_embeddings=[emb],
            n_results=top_k,
            include=["documents", "metadatas"],
        )
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            if doc not in seen and len(all_docs) < top_k:
                seen.add(doc)
                all_docs.append(doc)
                all_metas.append(meta)

    return all_docs[:top_k], all_metas[:top_k]


# ── RETRIEVAL ──────────────────────────────────────────────────────────────────
def retrieve(query: str, top_k: int, use_filter: bool = True,
             use_rewrite: bool = True, difficulty: str = "easy"):
    search_query, chunk_types, target_medicine, all_medicines = preprocess_query(
        query, use_rewrite, use_filter, difficulty
    )

    emb = embed(search_query)

    if difficulty == "hard" and len(all_medicines) > 1:
        multi_k = top_k + len(all_medicines) * 3
        docs, metas = _retrieve_multi_drug(
            emb, search_query, all_medicines, chunk_types=None, top_k=multi_k
        )
        docs, metas = rerank(search_query, docs, metas, top_n=top_k)
        return docs, metas

    if difficulty == "hard":
        effective_k = top_k + HIGH_CHUNK_K_BOOST + 2
    elif target_medicine and target_medicine in HIGH_CHUNK_MEDICINES:
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

    results     = collection.query(**query_kwargs)
    dense_docs  = results["documents"][0]
    dense_metas = results["metadatas"][0]
    active_types = chunk_types

    if chunk_types and len(dense_docs) < top_k:
        results      = collection.query(
            query_embeddings=[emb],
            n_results=effective_k,
            include=["documents", "metadatas"],
        )
        dense_docs   = results["documents"][0]
        dense_metas  = results["metadatas"][0]
        active_types = None

    if target_medicine:
        sparse_docs, sparse_metas = _bm25_retrieve(
            search_query, target_medicine, active_types, effective_k
        )
        dense_pairs  = list(zip(dense_docs, dense_metas))
        sparse_pairs = list(zip(sparse_docs, sparse_metas))
        merged_docs, merged_metas = rrf_merge(dense_pairs, sparse_pairs, effective_k)
    else:
        merged_docs, merged_metas = dense_docs, dense_metas

    merged_docs, merged_metas = rerank(
        search_query, merged_docs, merged_metas, top_n=top_k
    )
    merged_docs, merged_metas = rerank_by_medicine(
        merged_docs, merged_metas, target_medicine, top_k
    )

    return merged_docs, merged_metas


# ── SYSTEM PROMPT ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a clinical medical assistant. Answer the question using ONLY the context provided below.

Rules:
1. Use ONLY facts stated verbatim or clearly implied in the context. Do not add any clinical knowledge, inferences, or conclusions not explicitly in the context.
2. Always answer in English.
3. Include brand name as "BrandName (generic)" e.g. "Panadol (acetaminophen)". If only generic appears, use only that.
4. If the question is yes/no, begin with "Yes" or "No" followed by the medicine name. e.g. "Yes, Haldol (haloperidol) can cause muscle stiffness and tremor."
5. Otherwise open by directly addressing the question with the medicine name e.g. "Exelon (rivastigmine) can cause..."
6. 1-2 sentences for simple questions. 2-3 sentences for complex ones. Never exceed 3 sentences.
7. Do not start with "Based on the context" or "According to the provided information".
8. If the context only partially answers the question, state what it does say and stop. Never write sentences about what the context does not contain, does not specify, or does not provide.
9. Do not add "therefore", "caution is advised", "it is recommended", or any advisory language not explicitly in the context.
10. For multi-drug questions: name every drug and state the interaction first, then detail.
11. Never use "therefore", "thus", "hence", "as a result", or draw conclusions beyond what the context explicitly states.
12. Never write "the context does not", "no information is provided", or "it is unclear". Simply answer what is there and stop.
13. Never mention drug names that are not in the question or directly relevant to the answer. Do not mention combination product names like ZITUVIMET when asked about a single ingredient like metformin."""

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


# ── FAITHFULNESS GUARDRAIL (optional, off by default) ─────────────────────────
_GUARDRAIL_SYSTEM = """\
You are a medical fact-checker. You will be given a context and an answer.

Your task:
- Read every factual claim in the answer.
- Remove or rewrite any claim that is NOT directly supported by the context.
- Do NOT add new information — only keep or rewrite what is already in the answer.
- Keep the answer concise (2–4 sentences) and fluent.
- Output ONLY the corrected answer. No explanations, no preamble."""

def faithfulness_guardrail(answer: str, contexts: list[str]) -> str:
    context_block = "\n\n---\n\n".join(contexts)
    try:
        response = openai_client.chat.completions.create(
            model=GENERATOR_MODEL,   # uses same (cheaper) model as generator
            messages=[
                {"role": "system", "content": _GUARDRAIL_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context_block}\n\n"
                        f"Answer to verify:\n{answer}\n\n"
                        "Corrected answer:"
                    )
                }
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return answer


# ── IS_CORRECT ─────────────────────────────────────────────────────────────────
def is_correct(meta, expected):
    gen        = meta.get("generic_name", "").lower()
    brands_raw = meta.get("brand_names", "")

    if isinstance(brands_raw, str):
        brands = [b.strip().lower() for b in brands_raw.split(",") if b.strip()]
    else:
        brands = [b.lower() for b in brands_raw]

    exp = expected.lower()
    return exp == gen or exp in brands


# ── RETRIEVAL METRICS ──────────────────────────────────────────────────────────
def compute_retrieval(top_k):
    hits, mrr = 0, 0
    for q in questions:
        difficulty = q.get("difficulty", "easy")
        _, metas = retrieve(q["query"], top_k, args.chunk_filter,
                            args.query_rewrite, difficulty=difficulty)
        rank = next(
            (i + 1 for i, m in enumerate(metas) if is_correct(m, q["expected_generic"])),
            None
        )
        if rank:
            hits += 1
            mrr  += 1 / rank

    total = len(questions)
    return {f"hit_at_{top_k}": hits / total, "mrr": mrr / total}


# ── BUILD RAGAS DATASET ────────────────────────────────────────────────────────
def build_dataset(top_k):
    data = []
    print("Building dataset...")

    for q in tqdm(questions):
        difficulty = q.get("difficulty", "easy")
        contexts, _ = retrieve(
            q["query"], top_k, args.chunk_filter,
            args.query_rewrite, difficulty=difficulty
        )

        gen_k  = GEN_K_EASY if difficulty == "easy" else GEN_K_HARD
        prompt_contexts = contexts[:gen_k]

        answer = generate_answer(q["query"], prompt_contexts)

        # COST CUT 2: guardrail off by default; only runs when --guardrail passed
        if args.guardrail:
            answer = faithfulness_guardrail(answer, prompt_contexts)

        if args.debug:
            print(f"\nQUESTION [{difficulty}]: {q['query']}")
            print(f"TOP CHUNK:  {contexts[0][:200]}")
            print(f"ANSWER:     {answer[:200]}")

        data.append({
            "question":     q["query"],
            "answer":       answer,
            "contexts":     prompt_contexts,  # FIXED: match what LLM saw
            "ground_truth": q.get("ground_truth", q["expected_generic"]),
        })

    return Dataset.from_list(data)


# ── RUN RAGAS ──────────────────────────────────────────────────────────────────
def run_ragas(dataset):
    # COST CUT 5: context_precision excluded by default (per-chunk LLM calls)
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
        "ragas_faithfulness":      df["faithfulness"].mean(),
        "ragas_answer_relevancy":  df["answer_relevancy"].mean(),
        "ragas_context_recall":    df["context_recall"].mean(),
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

    with mlflow.start_run(run_name=args.run_name or f"run_top{top_k}"):
        mlflow.log_params({
            "top_k":                  top_k,
            "min_tokens":             MIN_TOKENS,
            "max_tokens":             MAX_TOKENS,
            "overlap_tokens":         OVERLAP_TOKENS,
            "generator_model":        GENERATOR_MODEL,
            "utility_model":          UTILITY_MODEL,
            "ragas_judge_model":      RAGAS_JUDGE_MODEL,
            "embedding_model":        "text-embedding-3-large",
            "query_rewrite":          args.query_rewrite,
            "chunk_filter":           args.chunk_filter,
            "chunk_classifier":       "llm_gpt4o_mini",
            "medicine_reranking":     True,
            "io_dual_type_search":    True,
            "high_chunk_k_boost":     HIGH_CHUNK_K_BOOST,
            "gen_k_easy":             GEN_K_EASY,
            "gen_k_hard":             GEN_K_HARD,
            "hybrid_search":          True,
            "bge_reranker":           True,
            "faithfulness_guardrail": args.guardrail,
            "full_ragas":             args.full_ragas,
            "parallel_preprocessing": True,
            "embedding_cache":        True,
            "test_set":               "english_direct_v4",
            "chunk_collection":       OPENAI_COLLECTION,
        })
        mlflow.log_metrics(metrics)

    print("\n✅ Logged to MLflow")