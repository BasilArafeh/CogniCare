import os
import json
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import chromadb

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ── CONFIG ─────────────────────────────────────────────
CHUNKS_FILE     = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medicines/all_medicine_chunks.json"
CHROMA_PATH     = "/Users/leensalman/Desktop/gp2/CogniCare/rag/vectorstore/chroma_db"
COLLECTION_NAME = "medicines_openai15"
BATCH_SIZE      = 100
MAX_BATCH       = 5000


# ── EMBEDDING ──────────────────────────────────────────
def embed_batch(client_oai, texts):
    response = client_oai.embeddings.create(
        input=texts,
        model="text-embedding-3-large"
    )
    return [r.embedding for r in response.data]


# ── METADATA SANITIZER ─────────────────────────────────
# ChromaDB only accepts str, int, float, bool as metadata values.
# Lists (like brand_names), None values, or any other type will cause
# silent errors or wrong filter results. This function ensures every
# value is a safe scalar before it reaches ChromaDB.
# brand_names list → joined as comma-separated string.
# is_correct() in the eval pipeline splits it back for comparison.
def sanitize_metadata(meta: dict) -> dict:
    sanitized = {}
    for k, v in meta.items():
        if isinstance(v, list):
            sanitized[k] = ", ".join(str(x) for x in v)
        elif isinstance(v, (str, int, float, bool)):
            sanitized[k] = v
        elif v is None:
            sanitized[k] = ""
        else:
            sanitized[k] = str(v)
    return sanitized


def main():
    client_oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ── LOAD DATA ──────────────────────────────────────
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks")

    # ── CHROMA ─────────────────────────────────────────
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # ── INDEXING ───────────────────────────────────────
    all_ids, all_docs, all_meta, all_embeds = [], [], [], []
    print("Indexing...")

    for i in tqdm(range(0, len(chunks), BATCH_SIZE)):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        embeddings = embed_batch(client_oai, texts)
        assert len(texts) == len(embeddings)

        for j, chunk in enumerate(batch):
            meta = chunk.get("metadata", {})
            clean_meta = sanitize_metadata({
                "generic_name": meta.get("generic_name", "").lower(),
                "brand_names":  meta.get("brand_names", ""),
                "chunk_type":   meta.get("chunk_type", "").lower(),
                "chunk_part":   meta.get("chunk_part", 1),
                "total_parts":  meta.get("total_parts", 1),
                "token_count":  meta.get("token_count", 0),
                "drug_class":   meta.get("drug_class", ""),
                "manufacturer": meta.get("manufacturer", "Unknown"),
                "source":       meta.get("source", "openFDA"),
            })
            all_ids.append(f"{chunk['chunk_id']}_{i}_{j}")
            all_docs.append(texts[j])
            all_meta.append(clean_meta)
            all_embeds.append(embeddings[j])

    # ── SAFETY CHECK ───────────────────────────────────
    print("Docs:",   len(all_docs))
    print("Embeds:", len(all_embeds))
    print("IDs:",    len(all_ids))
    assert len(all_docs) == len(all_embeds) == len(all_ids)

    # ── ADD TO CHROMA ──────────────────────────────────
    for i in range(0, len(all_docs), MAX_BATCH):
        collection.add(
            documents=all_docs[i:i+MAX_BATCH],
            embeddings=all_embeds[i:i+MAX_BATCH],
            metadatas=all_meta[i:i+MAX_BATCH],
            ids=all_ids[i:i+MAX_BATCH],
        )
    print("✅ Indexing complete")

    # ── VERIFY: basic retrieval ────────────────────────
    print("\nTesting basic retrieval...")
    test_query      = "What is paracetamol used for?"
    query_embedding = embed_batch(client_oai, [test_query])[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=3)
    for doc in results["documents"][0]:
        print("\n---")
        print(doc[:200])

    # ── VERIFY: chunk_type filter ──────────────────────
    # Sanity check for all 7 chunk types produced by chunk.py.
    # If any return 0 results, something went wrong with metadata storage.
    for ctype in [
        "side_effects", "dosage", "administration", "special_populations",
        "interactions_and_overdose", "storage", "identity_and_usage",
    ]:
        print(f"\nTesting chunk_type filter ({ctype})...")
        results_filtered = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"chunk_type": {"$in": [ctype]}},
        )
        filtered_docs = results_filtered["documents"][0]
        if filtered_docs:
            print(f"  ✅ {len(filtered_docs)} result(s) — {filtered_docs[0][:100]}")
        else:
            print(f"  ⚠️  WARNING: '{ctype}' returned 0 results — check metadata storage.")


if __name__ == "__main__":
    main()