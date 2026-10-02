KB_DIR = "data/knowledge_base"
MEMO_DIR = "data/memos"
INDEX_DIR = "data/index"
EVAL_DIR = "data/eval"
TOP_K = 5
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
THRESHOLDS = {"recall_at_5": 0.90, "faithfulness": 0.90, "answer_relevance": 0.90, "hallucination": 0.05, "p95_latency_s": 3.0}
# KB is UK-standards-only. User memos go to MEMO_DIR and are NEVER indexed.
KB_GLOB = "uk_*.txt"

