"""
CogniCare - RAG Evaluation Script (FIXED)
========================================
Compares BGE-M3 vs text-embedding-3-large on evaluation queries.

Metrics:
  - Hit@5       : is the correct chunk in the top 5 results?
  - MRR         : mean reciprocal rank of the correct chunk

Run:
  python run_eval.py
"""

import json
import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

# ── Load env ───────────────────────────────────────────
load_dotenv()

# ── Config ─────────────────────────────────────────────
EVAL_FILE         = "/Users/leensalman/Desktop/gp2/rag/evaluation/test_questions.json"
CHROMA_PATH       = "/Users/leensalman/Desktop/gp2/rag/vectorstore/chroma_db"
BGE_COLLECTION    = "medicines_bge"
OPENAI_COLLECTION = "medicines_openai"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
TOP_K             = 5

# ── Load eval questions ────────────────────────────────
with open(EVAL_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} evaluation questions")

# ── Load models ────────────────────────────────────────
print("Loading BGE-M3...")
bge_model = SentenceTransformer("BAAI/bge-m3")

print("Loading OpenAI client...")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Load ChromaDB collections (FIXED) ──────────────────
client = chromadb.PersistentClient(path=CHROMA_PATH)

bge_collection = client.get_collection(BGE_COLLECTION)
oai_collection = client.get_collection(OPENAI_COLLECTION)

print("Collections loaded:")
print(f" - {BGE_COLLECTION}: {bge_collection.count()} docs")
print(f" - {OPENAI_COLLECTION}: {oai_collection.count()} docs")

# ── Embedding functions (FIXED) ─────────────────────────
def embed_bge(query):
    return bge_model.encode(
        [query],
        prompt="Represent this sentence for searching relevant passages: ",
        normalize_embeddings=True
    )[0].tolist()

def embed_openai(query):
    response = openai_client.embeddings.create(
        input=[query],  # FIXED
        model="text-embedding-3-large"
    )
    return response.data[0].embedding

# ── Query ChromaDB ─────────────────────────────────────
def query_collection(collection, embedding, top_k=5):
    return collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["metadatas", "documents", "distances"]
    )

# ── Check correctness ──────────────────────────────────
def is_correct(metadata, expected_generic, expected_chunk_type):
    return (
        metadata.get("generic_name", "").lower() == expected_generic.lower()
        and metadata.get("chunk_type", "").lower() == expected_chunk_type.lower()
    )

# ── Compute MRR ─────────────────────────────────────────
def compute_mrr(rank):
    return 1.0 / rank if rank else 0.0

# ── Evaluation loop ─────────────────────────────────────
def run_eval(questions, collection, embed_fn, model_name):
    print(f"\n{'='*55}")
    print(f"Evaluating: {model_name}")
    print(f"{'='*55}")

    hits = 0
    mrr_total = 0.0
    failures = []
    by_category = {}

    for q in tqdm(questions, desc=model_name):

        # Embed query
        embedding = embed_fn(q["query"])

        # Query DB
        results = query_collection(collection, embedding, TOP_K)

        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]

        # Safety check (FIXED)
        if not metadatas:
            failures.append({
                "id": q["id"],
                "query": q["query"],
                "reason": "No results returned"
            })
            continue

        # Find rank of correct chunk
        rank = None
        for i, meta in enumerate(metadatas):
            if is_correct(meta, q["expected_generic"], q["expected_chunk_type"]):
                rank = i + 1
                break

        hit = rank is not None and rank <= TOP_K
        mrr = compute_mrr(rank)

        if hit:
            hits += 1
        else:
            failures.append({
                "id": q["id"],
                "query": q["query"],
                "category": q["category"],
                "expected": f"{q['expected_generic']} / {q['expected_chunk_type']}",
                "got": f"{metadatas[0].get('generic_name')} / {metadatas[0].get('chunk_type')}"
            })

        mrr_total += mrr

        # Category tracking
        cat = q["category"]
        if cat not in by_category:
            by_category[cat] = {"hits": 0, "total": 0, "mrr": 0.0}

        by_category[cat]["total"] += 1
        by_category[cat]["mrr"] += mrr

        if hit:
            by_category[cat]["hits"] += 1

    total = len(questions)
    hit_at_5 = hits / total
    mrr_score = mrr_total / total

    # ── Print results ───────────────────────────────────
    print(f"\nResults for {model_name}:")
    print(f"  Hit@5 : {hit_at_5:.2%}")
    print(f"  MRR   : {mrr_score:.4f}")

    print(f"\nBy category:")
    for cat, scores in by_category.items():
        cat_hit = scores["hits"] / scores["total"]
        cat_mrr = scores["mrr"] / scores["total"]
        print(f"  {cat:<25} Hit@5: {cat_hit:.2%}  MRR: {cat_mrr:.4f}")

    if failures:
        print(f"\nFailure cases ({len(failures)}):")
        for f in failures[:5]:  # limit output
            print(f"  [{f['id']}] {f['query'][:60]}")
            print(f"      Expected : {f.get('expected', '-')}")
            print(f"      Got      : {f.get('got', f.get('reason'))}")

    return {
        "model": model_name,
        "hit_at_5": hit_at_5,
        "mrr": mrr_score,
        "failures": failures,
        "by_category": by_category
    }

# ── Main ───────────────────────────────────────────────
if __name__ == "__main__":

    bge_results = run_eval(
        questions,
        bge_collection,
        embed_bge,
        "BGE-M3"
    )

    oai_results = run_eval(
        questions,
        oai_collection,
        embed_openai,
        "text-embedding-3-large"
    )

    # ── Final comparison ────────────────────────────────
    print(f"\n{'='*55}")
    print("FINAL COMPARISON")
    print(f"{'='*55}")
    print(f"{'Model':<30} {'Hit@5':>8} {'MRR':>8}")
    print(f"{'-'*50}")

    for r in [bge_results, oai_results]:
        print(f"{r['model']:<30} {r['hit_at_5']:>8.2%} {r['mrr']:>8.4f}")

    winner = max([bge_results, oai_results], key=lambda x: x["hit_at_5"])

    print(f"\n🏆 Winner: {winner['model']} (Hit@5 = {winner['hit_at_5']:.2%})")

    # ── Save results ────────────────────────────────────
    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump([bge_results, oai_results], f, indent=2, ensure_ascii=False)

    print("\n✅ Results saved to eval_results.json")