import os
import json
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import chromadb

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CHUNKS_FILE     = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/documents/chunks.json"
CHROMA_PATH     = "/Users/leensalman/Desktop/gp2/CogniCare/rag/vectorstore/chroma_db"
COLLECTION_NAME = "documents_collection1"
BATCH_SIZE      = 100
MAX_BATCH       = 5000


# ── EMBEDDING ──────────────────────────────────────────────────────────────────
def embed_batch(client_oai, texts):
    response = client_oai.embeddings.create(
        input=texts,
        model="text-embedding-3-large"
    )
    return [r.embedding for r in response.data]


# ── METADATA SANITIZER ─────────────────────────────────────────────────────────
# ChromaDB only accepts str, int, float, bool as metadata values.
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

    # ── LOAD DATA ──────────────────────────────────────────────────────────────
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks")

    # ── CHROMA ─────────────────────────────────────────────────────────────────
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # ── INDEXING ───────────────────────────────────────────────────────────────
    all_ids, all_docs, all_meta, all_embeds = [], [], [], []
    print("Indexing...")

    for i in tqdm(range(0, len(chunks), BATCH_SIZE)):
        batch = chunks[i:i + BATCH_SIZE]

        # Embed the embedding_text field (title + content), not raw content
        texts = [c["embedding_text"] for c in batch]

        embeddings = embed_batch(client_oai, texts)
        assert len(texts) == len(embeddings)

        for j, chunk in enumerate(batch):
            clean_meta = sanitize_metadata({
                "title":    chunk.get("title", ""),
                "section":  chunk.get("section", ""),
                "category": chunk.get("category", ""),
                "source":   chunk.get("file_name", ""),
            })
            all_ids.append(chunk["id"])
            all_docs.append(texts[j])
            all_meta.append(clean_meta)
            all_embeds.append(embeddings[j])

    # ── SAFETY CHECK ───────────────────────────────────────────────────────────
    print("Docs:",   len(all_docs))
    print("Embeds:", len(all_embeds))
    print("IDs:",    len(all_ids))
    assert len(all_docs) == len(all_embeds) == len(all_ids)

    # ── ADD TO CHROMA ──────────────────────────────────────────────────────────
    for i in range(0, len(all_docs), MAX_BATCH):
        collection.add(
            documents=all_docs[i:i + MAX_BATCH],
            embeddings=all_embeds[i:i + MAX_BATCH],
            metadatas=all_meta[i:i + MAX_BATCH],
            ids=all_ids[i:i + MAX_BATCH],
        )
    print("✅ Indexing complete")

    # ── VERIFY: basic retrieval ────────────────────────────────────────────────
    print("\nTesting basic retrieval...")
    test_query      = "What are the early signs of Alzheimer's disease?"
    query_embedding = embed_batch(client_oai, [test_query])[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=3)
    for doc in results["documents"][0]:
        print("\n---")
        print(doc[:200])

    # ── VERIFY: category filter ────────────────────────────────────────────────
    # Sanity check that all three categories are present in the collection.
    for cat in [
        "alzheimers_and_other_sicknesses",
        "communication_guidelines",
        "mental_health",
    ]:
        print(f"\nTesting category filter ({cat})...")
        results_filtered = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"category": {"$eq": cat}},
        )
        filtered_docs = results_filtered["documents"][0]
        if filtered_docs:
            print(f"  ✅ {len(filtered_docs)} result(s) — {filtered_docs[0][:100]}")
        else:
            print(f"  ⚠️  WARNING: '{cat}' returned 0 results — check metadata storage.")


if __name__ == "__main__":
    main()
