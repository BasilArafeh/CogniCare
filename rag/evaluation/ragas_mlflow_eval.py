"""
cognicare_eval.py  —  CogniCare RAG Evaluation (with Web Fallback)
==================================================================

Architecture
------------
  1. Brand → Generic   : dictionary lookup        (0 API calls)
  2. Drug match        : exact ChromaDB filter     (0 API calls)
  3. Field selection   : keyword rules             (0 API calls)
  4. Answer generation : gpt-4o                   (1 API call)
  5. Web fallback      : if local answer is empty  (1 extra API call)
  6. Evaluation        : LLM-as-judge             (1 API call)

Total per question: 2 calls (no fallback) or 3 calls (with fallback)
"""

import os
import json
import math
import csv
import argparse
from tqdm import tqdm
from dotenv import load_dotenv

import mlflow
from openai import OpenAI
import chromadb

from CogniCare.rag.pipeline.web_fallback import WebFallback

load_dotenv()

# ── CONFIG ─────────────────────────────────────────────────────────────────────
EVAL_FILE         = os.path.join(os.path.dirname(__file__), "test_questions.json")
CHROMA_PATH       = os.path.expanduser("/Users/leensalman/Desktop/gp2/CogniCare/rag/vectorstore/chroma_db")
OPENAI_COLLECTION = "medicines_openai11"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
MLFLOW_EXPERIMENT = "CogniCare-RAG-Evaluation"
CACHE_DIR         = os.path.join(os.path.dirname(__file__), "cache")

mlflow.set_tracking_uri("file:///Users/leensalman/Desktop/gp2/mlruns")

GENERATOR_MODEL = "gpt-4o"
JUDGE_MODEL     = "gpt-4o-mini"

# ── ARGS ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--sample",          type=int,  default=None)
parser.add_argument("--run-name",        type=str,  default=None)
parser.add_argument("--debug",           action="store_true", default=False)
parser.add_argument("--no-web-fallback", action="store_true", default=False,
                    help="Disable web fallback (faster, for comparison)")
args = parser.parse_args()

os.makedirs(CACHE_DIR, exist_ok=True)

# ── LOAD QUESTIONS ─────────────────────────────────────────────────────────────
with open(EVAL_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)
if args.sample:
    questions = questions[:args.sample]
print(f"Loaded {len(questions)} questions")

# ── CLIENTS ────────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0, max_retries=3)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_collection(OPENAI_COLLECTION)
web_fallback  = WebFallback(openai_client, model=JUDGE_MODEL)
print(f"Collection: {collection.count()} docs")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — BRAND → GENERIC LOOKUP
# ══════════════════════════════════════════════════════════════════════════════

BRAND_TO_GENERIC: dict[str, str] = {
    "aricept":    "donepezil",
    "exelon":     "rivastigmine",
    "reminyl":    "galantamine",
    "razadyne":   "galantamine",
    "ebixa":      "memantine",
    "namenda":    "memantine",
    "concor":     "bisoprolol",
    "zebeta":     "bisoprolol",
    "lipitor":    "atorvastatin",
    "crestor":    "rosuvastatin",
    "zocor":      "simvastatin",
    "coumadin":   "warfarin",
    "plavix":     "clopidogrel",
    "lasix":      "furosemide",
    "lanoxin":    "digoxin",
    "coversyl":   "perindopril",
    "zestril":    "lisinopril",
    "prinivil":   "lisinopril",
    "glucophage": "metformin",
    "lantus":     "insulin glargine",
    "toujeo":     "insulin glargine",
    "zoloft":     "sertraline",
    "prozac":     "fluoxetine",
    "haldol":     "haloperidol",
    "xanax":      "alprazolam",
    "valium":     "diazepam",
    "ativan":     "lorazepam",
    "tegretol":   "carbamazepine",
    "sinemet":    "levodopa carbidopa",
    "panadol":    "acetaminophen",
    "tylenol":    "acetaminophen",
    "brufen":     "ibuprofen",
    "advil":      "ibuprofen",
    "nurofen":    "ibuprofen",
    "nexium":     "esomeprazole",
}

def resolve_generic(query: str) -> str | None:
    q = query.lower()
    for brand in sorted(BRAND_TO_GENERIC, key=len, reverse=True):
        if brand in q:
            return BRAND_TO_GENERIC[brand]
    known_generics = set(BRAND_TO_GENERIC.values())
    for generic in sorted(known_generics, key=len, reverse=True):
        if generic in q:
            return generic
    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — QUESTION CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("interactions_and_overdose", [
        "interact", "interaction", "together with", "taken with", "combine",
        "combination", "overdose", "too much", "excess", "toxicity", "toxic",
        "contraindic", "dangerous with", "not be taken", "should not take",
        "avoid with", "dangerous if",
    ]),
    ("side_effects", [
        "side effect", "adverse", "cause", "causes", "causing", "reaction",
        "symptom", "warning", "risk", "safe", "safety", "tolerat",
        "stiffness", "shaking", "tremor", "dizziness", "nausea", "vomiting",
        "cough", "bruise", "bleeding", "muscle pain", "confusion", "sedation",
        "fatigue", "drowsy", "drowsiness", "elderly", "safe for",
    ]),
    ("dosage", [
        "dose", "dosage", "how much", "how many", "how often", "frequency",
        "how to take", "when to take", "morning", "night", "bedtime",
        "before meal", "after meal", "with food", "apply", "patch",
        "starting dose", "maximum", "minimum", "twice", "once daily",
        "how should", "taken before", "taken after",
    ]),
    ("storage", [
        "store", "storage", "keep", "refrigerat", "temperature",
        "shelf life", "expir",
    ]),
    ("identity_and_usage", [
        "what is", "used for", "treat", "prescribed for", "condition",
        "what does", "what kind", "type of", "class", "indication",
        "approved for", "works for",
    ]),
]

def classify_question(query: str) -> str:
    q = query.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in q for kw in keywords):
            return category
    return "identity_and_usage"


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — DIRECT RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════════

def retrieve_chunks(generic_name: str, chunk_type: str, top_n: int = 3) -> list[str]:
    try:
        result = collection.get(
            where={
                "$and": [
                    {"generic_name": {"$eq": generic_name}},
                    {"chunk_type":   {"$eq": chunk_type}},
                ]
            },
            include=["documents", "metadatas"],
            limit=top_n,
        )
        if result["documents"]:
            pairs = sorted(
                zip(result["documents"], result["metadatas"]),
                key=lambda x: x[1].get("chunk_part", 1)
            )
            return [doc for doc, _ in pairs]
    except Exception:
        pass
    return []


def retrieve_all_chunks(generic_name: str, top_n: int = 5) -> list[str]:
    """Pull all chunk types for a drug when specific type has no info."""
    try:
        result = collection.get(
            where={"generic_name": {"$eq": generic_name}},
            include=["documents", "metadatas"],
            limit=top_n,
        )
        if result["documents"]:
            pairs = sorted(
                zip(result["documents"], result["metadatas"]),
                key=lambda x: x[1].get("chunk_part", 1)
            )
            return [doc for doc, _ in pairs]
    except Exception:
        pass
    return []


def retrieve(query: str, expected_generic: str) -> tuple[list[str], str, str]:
    generic    = resolve_generic(query) or expected_generic.lower()
    chunk_type = classify_question(query)
    contexts   = retrieve_chunks(generic, chunk_type,
                                 top_n=5 if chunk_type == "interactions_and_overdose" else 3)

    # For interactions/overdose also pull side_effects
    if chunk_type == "interactions_and_overdose":
        extra = retrieve_chunks(generic, "side_effects", top_n=2)
        seen  = set(contexts)
        for doc in extra:
            if doc not in seen:
                contexts.append(doc)
                seen.add(doc)

    # For dosage also pull identity chunk
    if chunk_type == "dosage" and len(contexts) < 2:
        extra = retrieve_chunks(generic, "identity_and_usage", top_n=1)
        contexts += [d for d in extra if d not in set(contexts)]

    # If still thin — pull all chunks for this drug
    if len(contexts) < 2:
        all_chunks = retrieve_all_chunks(generic, top_n=5)
        seen = set(contexts)
        for doc in all_chunks:
            if doc not in seen:
                contexts.append(doc)
                seen.add(doc)

    if not contexts:
        contexts = retrieve_chunks(generic, "identity_and_usage", top_n=2)

    return contexts, generic, chunk_type


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — ANSWER GENERATION
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are CogniCare, a clinical medical information assistant for healthcare providers
and caregivers. Your answers are grounded exclusively in the provided drug database
context. You do not have opinions and you do not practice medicine.

════════════════════════════════════════════════
GROUNDING RULES  (non-negotiable)
════════════════════════════════════════════════
1. SOURCE RESTRICTION
   Answer ONLY from the context provided below.
   If the specific information is not in the context, you MUST output exactly:
   "This information is not available in the provided context."
   Never fill gaps with general medical knowledge, training data, or assumptions.
   It is always better to admit a gap than to hallucinate an answer.

2. NO INFERENCE
   Do not draw conclusions beyond what the context explicitly states.
   Do not combine facts from different sentences to create new claims.
   Do not say "likely", "probably", or "may" unless the context uses those words.

3. HALLUCINATION CHECK
   Before finalising your answer, mentally verify: can every sentence be pointed
   to a specific line in the context? If not, remove that sentence.

════════════════════════════════════════════════
FORMAT RULES
════════════════════════════════════════════════
4. OPENING
   Always open by naming the drug directly.
   Use "BrandName (generic_name)" format when both appear in context.
   Example: "Aricept (donepezil) is indicated for..."
   Never open with "Based on the context", "According to", or "The medication".

5. LENGTH
   2–4 sentences for simple factual questions.
   Up to 6 sentences for complex questions (interactions, overdose, multi-drug).
   Never pad with disclaimers or repetition.

6. LANGUAGE
   Always respond in English regardless of the question language.
   Use clinical but accessible language — avoid jargon unless it is in the context.

════════════════════════════════════════════════
CLINICAL CONTENT RULES
════════════════════════════════════════════════
7. DRUG NAMES
   Always use both brand and generic name on first mention if both appear in context.
   For subsequent mentions use the generic name only.

8. DOSAGE QUESTIONS
   State the dose exactly as written in context — never round or paraphrase numbers.
   If the context gives a range, state the full range.

9. SIDE EFFECTS QUESTIONS
   List the specific effects mentioned in context.
   Do not add "consult your doctor" or safety advice unless the context states it.

10. INTERACTION QUESTIONS
    Name every drug involved in the interaction.
    State the consequence of the interaction as written in context.
    If severity is mentioned (e.g. "serious", "contraindicated"), include it.

11. OVERDOSE QUESTIONS
    If context describes overdose symptoms or management, state them exactly.
    Never add emergency instructions not present in the context.

12. PARTIAL CONTEXT
    If the context partially addresses the question, answer what it supports,
    then add one sentence: "The context does not specify [missing detail]."
    Do not say the information is unavailable if part of it is available.

════════════════════════════════════════════════
WHAT YOU MUST NEVER DO
════════════════════════════════════════════════
- Never recommend a specific treatment or course of action
- Never contradict the context even if you believe it is outdated
- Never mention that you are an AI or that you have a knowledge cutoff
- Never say "I cannot help with that" — either answer from context or say it is not in the context
- Never use bullet points unless the context itself lists items
- Never start a sentence with "I"\
"""

def generate_answer(query: str, contexts: list[str]) -> str:
    if not contexts:
        return "This information is not available in the provided context."
    context_block = "\n\n---\n\n".join(contexts)
    r = openai_client.chat.completions.create(
        model=GENERATOR_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context_block}\n\nQuestion: {query}\n\nAnswer:"},
        ],
        temperature=0,
    )
    return r.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — LLM-AS-JUDGE
# ══════════════════════════════════════════════════════════════════════════════

JUDGE_SYSTEM = """\
You are a medical QA evaluator. Score the answer on 3 criteria.
Output ONLY a JSON object with keys: correctness, completeness, faithfulness.
Each score is 1-5 where 5=perfect, 4=good, 3=partial, 2=mostly wrong, 1=completely wrong.

correctness  : Is the answer factually accurate given the ground truth?
completeness : Does the answer cover the key facts in the ground truth?
faithfulness : Does the answer stick to facts without hallucination?

Output format (JSON only, no other text):
{"correctness": N, "completeness": N, "faithfulness": N}"""

def judge_answer(query: str, answer: str, ground_truth: str) -> dict:
    prompt = (
        f"Question: {query}\n\n"
        f"Ground Truth: {ground_truth}\n\n"
        f"Answer to evaluate: {answer}"
    )
    try:
        r = openai_client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0,
            max_tokens=60,
        )
        raw = r.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        scores = json.loads(raw)
        return {
            "correctness":  float(scores.get("correctness",  0)),
            "completeness": float(scores.get("completeness", 0)),
            "faithfulness": float(scores.get("faithfulness", 0)),
        }
    except Exception as e:
        if args.debug:
            print(f"  [judge error] {e}")
        return {"correctness": 0.0, "completeness": 0.0, "faithfulness": 0.0}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def is_correct_retrieval(generic_found: str, expected: str) -> bool:
    return generic_found.lower().strip() == expected.lower().strip()


if __name__ == "__main__":
    results        = []
    hit_count      = 0
    fallback_count = 0

    print(f"\nWeb fallback: {'OFF' if args.no_web_fallback else 'ON'}")
    print("Running pipeline...")

    for q in tqdm(questions):
        # ── Retrieve ───────────────────────────────────────────────────────────
        contexts, resolved_generic, chunk_type = retrieve(
            q["query"], q["expected_generic"]
        )

        hit = is_correct_retrieval(resolved_generic, q["expected_generic"])
        if hit:
            hit_count += 1

        # ── Generate local answer ──────────────────────────────────────────────
        local_answer = generate_answer(q["query"], contexts)

        local_answer = generate_answer(q["query"], contexts)

        # ── Web fallback if local answer is empty ──────────────────────────────
        used_fallback = False
        source        = "local"
        source_url    = None

        if not args.no_web_fallback:
            fallback_result = web_fallback.answer_with_fallback(
                query=q["query"],
                local_answer=local_answer,
                generic_name=resolved_generic,
            )
            final_answer  = fallback_result.answer
            used_fallback = fallback_result.used_fallback
            source        = fallback_result.source
            source_url    = fallback_result.source_url

            if used_fallback:
                fallback_count += 1
                if args.debug:
                    print(f"  [WEB FALLBACK] {q['query'][:60]}")
                    print(f"  [WEB SOURCE]   {source_url}")
        else:
            final_answer = local_answer

        # ── Judge ──────────────────────────────────────────────────────────────
        scores = judge_answer(q["query"], final_answer, q["ground_truth"])

        if args.debug:
            print(f"\n{'─'*60}")
            print(f"Q [{q.get('difficulty','?')}]: {q['query']}")
            print(f"Resolved: {resolved_generic} | Type: {chunk_type} | Source: {source}")
            print(f"A: {final_answer[:200]}")
            print(f"Scores: {scores}")

        results.append({
            "id":               q["id"],
            "difficulty":       q.get("difficulty", "easy"),
            "query":            q["query"],
            "expected_generic": q["expected_generic"],
            "resolved_generic": resolved_generic,
            "chunk_type":       chunk_type,
            "retrieval_hit":    hit,
            "ground_truth":     q["ground_truth"],
            "local_answer":     local_answer,
            "final_answer":     final_answer,
            "used_fallback":    used_fallback,
            "source":           source,
            "source_url":       source_url or "",
            "n_contexts":       len(contexts),
            **scores,
        })

    # ── Metrics ────────────────────────────────────────────────────────────────
    total = len(results)

    def avg(key):
        vals = [r[key] for r in results if r[key] > 0]
        return sum(vals) / len(vals) if vals else 0.0

    def avg_norm(key):
        return (avg(key) - 1) / 4

    metrics = {
        "retrieval_hit_rate": hit_count / total,
        "web_fallback_rate":  fallback_count / total,
        "correctness_raw":    avg("correctness"),
        "completeness_raw":   avg("completeness"),
        "faithfulness_raw":   avg("faithfulness"),
        "correctness":        avg_norm("correctness"),
        "completeness":       avg_norm("completeness"),
        "faithfulness":       avg_norm("faithfulness"),
        "overall_score":      avg_norm("correctness") * 0.4
                            + avg_norm("completeness") * 0.4
                            + avg_norm("faithfulness") * 0.2,
    }

    for diff in ["easy", "medium"]:
        subset = [r for r in results if r["difficulty"] == diff]
        if subset:
            for key in ["correctness", "completeness", "faithfulness"]:
                vals = [r[key] for r in subset if r[key] > 0]
                metrics[f"{diff}_{key}"] = (
                    (sum(vals) / len(vals) - 1) / 4 if vals else 0.0
                )

    print(f"\n{'='*50}")
    print("── RESULTS ──")
    print(f"{'='*50}")
    print(f"retrieval_hit_rate : {metrics['retrieval_hit_rate']:.4f}")
    print(f"web_fallback_rate  : {metrics['web_fallback_rate']:.4f}  ({fallback_count}/{total} questions used web)")
    print(f"correctness  (0-1) : {metrics['correctness']:.4f}  (raw: {metrics['correctness_raw']:.2f}/5)")
    print(f"completeness (0-1) : {metrics['completeness']:.4f}  (raw: {metrics['completeness_raw']:.2f}/5)")
    print(f"faithfulness (0-1) : {metrics['faithfulness']:.4f}  (raw: {metrics['faithfulness_raw']:.2f}/5)")
    print(f"overall_score      : {metrics['overall_score']:.4f}")

    if "easy_correctness" in metrics:
        print(f"\n── By difficulty ──")
        for diff in ["easy", "medium"]:
            if f"{diff}_correctness" in metrics:
                print(f"  {diff:6s}: corr={metrics[f'{diff}_correctness']:.3f}  "
                      f"comp={metrics[f'{diff}_completeness']:.3f}  "
                      f"faith={metrics[f'{diff}_faithfulness']:.3f}")

    # ── Save CSV ───────────────────────────────────────────────────────────────
    csv_path = os.path.join(
        os.path.dirname(__file__),
        f"eval_results_{args.run_name or 'run'}.csv"
    )
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nPer-question results → {csv_path}")

    # ── MLflow ─────────────────────────────────────────────────────────────────
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    run_name = args.run_name or "web_fallback"
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({
            "generator_model":    GENERATOR_MODEL,
            "judge_model":        JUDGE_MODEL,
            "retrieval_strategy": "exact_metadata_filter",
            "web_fallback":       not args.no_web_fallback,
            "n_questions":        total,
            "collection":         OPENAI_COLLECTION,
        })
        mlflow.log_metrics({k: v for k, v in metrics.items() if not math.isnan(v)})

    print(f"\n✅ Logged to MLflow (run: {run_name})")
    web_calls = fallback_count if not args.no_web_fallback else 0
    print(f"API calls: {total * 2 + web_calls} total  "
          f"({total} generate + {total} judge + {web_calls} web fallback)")