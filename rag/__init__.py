# RAG ingestion package root for CogniCare.

import os

# Import-time defaults so any `import rag.…` path runs before `transformers` / `sentence_transformers`.
# Helps Windows noise (oneDNN, absl stderr) and keeps TF/Flax from participating in rerank loads.
_VARS = (
    ("TRANSFORMERS_NO_TF", "1"),
    ("TRANSFORMERS_NO_FLAX", "1"),
    ("TF_CPP_MIN_LOG_LEVEL", "3"),
    ("TF_ENABLE_ONEDNN_OPTS", "0"),
    ("TOKENIZERS_PARALLELISM", "false"),
    # Windows + PyTorch/oneDMKL: noisy defaults can segfault/fail during CrossEncoder load.
    ("OMP_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("KMP_DUPLICATE_LIB_OK", "TRUE"),
)
for kv in _VARS:
    os.environ.setdefault(kv[0], kv[1])
