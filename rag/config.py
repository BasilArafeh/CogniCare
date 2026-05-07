"""Central tuning knobs for CogniCare RAG (chunking reads these; no ingestion logic here)."""

from pathlib import Path

from dotenv import load_dotenv

# Same shared `.env` as ai_agent (`cognicare/.env`).
_COGNICARE_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_COGNICARE_ROOT / ".env")

# --- Paths (repository `rag/` package root) ---
RAG_ROOT = Path(__file__).resolve().parent
DOCUMENTS_ROOT = RAG_ROOT / "data" / "documents"
MEDICINES_ROOT = RAG_ROOT / "data" / "medicines"

# --- Chunking: medical PDFs (token-based, tiktoken) ---
MEDICAL_CHUNK_SIZE_TOKENS = 750
MEDICAL_CHUNK_OVERLAP_TOKENS = 110
TIKTOKEN_ENCODING_NAME = "cl100k_base"

# --- Chunking: medication JSON (token-based; same units as medical) ---
MEDICATION_CHUNK_SIZE_TOKENS = 750
MEDICATION_CHUNK_OVERLAP_TOKENS = 110
MEDICATION_SECONDARY_SPLIT_THRESHOLD = 750

# --- Embedding (OpenAI) ---
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
EMBEDDING_BATCH_SIZE = 50
EMBEDDING_BATCH_SLEEP_SEC = 0.5
EMBEDDING_MAX_RETRIES = 5

# --- Retrieval / reranking ---
RETRIEVAL_INITIAL_K = 10
RETRIEVAL_FINAL_K = 6
RERANKER_MODEL = "BAAI/bge-reranker-base"

# Hybrid BM25 + vector (weighted reciprocal-rank fusion). When False, pure vector retrieval.
HYBRID_SEARCH_ENABLED = True
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6

# --- Answer generation ---
GENERATION_MODEL = "gpt-4o-mini"
GENERATION_TEMPERATURE = 0.2
