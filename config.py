"""All experiment settings in one place. Change values here, not in the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
REPORT = ROOT / "report"

# ---------- Knowledge base (frozen after the first download) ----------
CORPUS_URLS = {
    "applications": "https://kubernetes.io/docs/tasks/debug/debug-application/_print/",
    "clusters": "https://kubernetes.io/docs/tasks/debug/debug-cluster/_print/",
}
PASSAGE_TOKENS = 250          # target passage size (approximate tokens)

# ---------- The LLM under test (local, via Ollama) ----------
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "modelscope.cn/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"
THINK = None                  # set to False for "thinking" models (e.g. qwen3) to switch thinking off
NUM_CTX = 16384               # context window; must fit the baseline prompts
SEED = 0
TEMPERATURE = 0.0
FREE_MAX_TOKENS = 1024        # safety cap for free-form answers (V0, V1)
BUDGET_MAX_TOKENS = 150       # T4 output cap (V2, V3, VO)

# ---------- Retrieval ----------
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
BASELINE_K = 10               # V0/V2: number of whole sections ("documents")
CANDIDATES = 20               # T1: passages retrieved before reranking
KMAX = 4                      # T1: maximum passages kept
TAU = 0.0                     # T1: chosen from the sweep (no TAU passed the rule for V3; fallback: most correct V3)
TAU_SWEEP = [-1.5, 0.0, 1.0, 2.0, 2.5, 3.0]   # covers the overlap of answerable and unanswerable top scores

# ---------- Experiment ----------
REPEATS = 3                   # repeats per question for latency
ABSTAIN_TEXT = "I cannot find this in the documentation."
NONINFERIORITY_POINTS = 3.0   # max allowed drop in correctness (percentage points)

# ---------- Judge (the grader) ----------
# backend "ollama": a local model (use a different family than LLM_MODEL)
# backend "openai": any OpenAI-compatible API (OpenAI, DeepSeek, Qwen/DashScope, ...)
JUDGE = {
    "backend": "openai",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",   # only used for backend "openai"
    "api_key_env": "JUDGE_API_KEY",              # name of the environment variable with your key
}

# ---------- Extra analyses ----------
CV_FOLDS, CV_REPEATS = 5, 20            # cross-validated TAU: stratified k-fold, repeated with new shuffles
HW_NAME = "Apple M4 (MacBook)"
HW_MEMORY_BANDWIDTH_GB_S = 120          # Apple's published unified-memory bandwidth for the M4 chip
SCALE_QUERIES_PER_DAY = 100_000         # volume for the scale projection
PRICE_INPUT_PER_M = None                # API price per 1M input tokens (fill in from the provider's pricing page)
PRICE_OUTPUT_PER_M = None               # API price per 1M output tokens
PRICE_CURRENCY = "USD"
