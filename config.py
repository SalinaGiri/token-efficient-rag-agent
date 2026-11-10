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
LLM_MODEL = "llama3.1:8b"     # set to the exact model you pulled with `ollama pull`
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
TAU = 0.0                     # T1: relevance threshold (set after `python run.py sweep`)
TAU_SWEEP = [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0]   # adjust after `python run.py scores`

# ---------- Experiment ----------
REPEATS = 3                   # repeats per question for latency
ABSTAIN_TEXT = "I cannot find this in the documentation."
NONINFERIORITY_POINTS = 3.0   # max allowed drop in correctness (percentage points)

# ---------- Judge (the grader) ----------
# backend "ollama": a local model (use a different family than LLM_MODEL)
# backend "openai": any OpenAI-compatible API (OpenAI, DeepSeek, Qwen/DashScope, ...)
JUDGE = {
    "backend": "ollama",
    "model": "qwen2.5:7b",
    "base_url": "https://api.deepseek.com/v1",   # only used for backend "openai"
    "api_key_env": "JUDGE_API_KEY",              # name of the environment variable with your key
}
