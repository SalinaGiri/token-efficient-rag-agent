# Fewer, Better Tokens

A small experiment on **token-efficient retrieval-augmented generation (RAG)** for an operational knowledge
assistant. A baseline agent is compared with token-optimised variants on 40 questions about the Kubernetes
troubleshooting documentation. The comparison covers tokens, latency (split into prefill and decode),
correctness, citations and abstention.

Technical exercise for internship 2026-INT-298 (*Token-Efficient AI-Agent Design for an Operational Knowledge Hub*).

## Idea in one paragraph

LLM inference has two phases: **prefill** processes all input tokens in parallel (compute-bound), and **decode**
generates output tokens one at a time (memory-bandwidth-bound). So the experiment tests one technique per phase:

- **T1 Adaptive retrieval** (input side): retrieve 20 passages, rerank them with a cross-encoder, and keep only
  passages scoring at least `TAU` (maximum 4). If none qualifies, the agent answers "not found" **without calling the LLM**.
- **T4 Output budgeting** (output side): an answer contract (answer first, at most 3 sentences, citations) and a
  150-token cap.

| Variant | Retrieval | Output |
|---|---|---|
| V0 Baseline | top-10 whole sections | free-form |
| V1 | T1 adaptive passages | free-form |
| V2 | top-10 whole sections | T4 budget |
| V3 Optimised | T1 adaptive passages | T4 budget |
| VO Oracle | gold passages only | T4 budget |

Headline metric: **TCCA, tokens per correct cited answer** = total tokens ÷ answers that are correct *and* cite a
passage from the right section (for unanswerable questions: a correct "not found").

## Project structure

```
config.py              all settings (model names, thresholds, repeats)
run.py                 one entry point for every step
data/questions.csv     40 test questions (25 single, 8 multi, 7 unanswerable)
data/gold.csv          gold passages per question (created by `run.py gold`, then checked by hand)
data/raw/              frozen, dated copy of the documentation
src/corpus.py          download + split into sections and ~250-token passages
src/retrieval.py       embeddings (MiniLM), reranker (cross-encoder), baseline and adaptive retrieval
src/llm.py             Ollama client (measures prefill and decode separately) + OpenAI-compatible judge client
src/prompts.py         free-form and budgeted prompts, judge prompt
src/agent.py           the five variants and the experiment loop (resumable)
src/judge.py           grading + 20% sample for manual checking
src/analyze.py         metrics, latency model, McNemar test, bootstrap CI, failure taxonomy
report/                figure and PDF builders (filled automatically by `run.py analyze`)
tests/test_pipeline.py offline test with fake models
```

## Setup (macOS, Apple Silicon)

1. Install **Ollama** from ollama.com and **Python 3.11+** from python.org.
2. Pull the model under test (and a judge model of a *different* family if you judge locally):
   ```
   ollama pull llama3.1:8b
   ollama pull qwen2.5:7b
   ```
   Put the exact names in `config.py` (`LLM_MODEL`, `JUDGE["model"]`).
3. Create a virtual environment **inside the project folder** (deleting the folder later removes everything):
   ```
   cd token-efficient-rag-agent
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m tests.test_pipeline        # should end with ALL TESTS PASSED
   ```

## Running the experiment

Keep the Mac plugged in and close other heavy apps while measuring.

| Step | Command | What to do afterwards |
|---|---|---|
| 1 | `python run.py fetch` | Downloads the docs once and splits them. Check the counts it prints. |
| 2 | `python run.py gold` | **Open `data/gold.csv` and check every row**, especially rows marked CHECK. Edit passage IDs if needed. |
| 3 | `python run.py scores` | Look at the score ranges and adjust `TAU_SWEEP` in `config.py` if needed. |
| 4 | `python run.py sweep` | Tries every threshold once and suggests a `TAU`. Set `TAU` in `config.py`. |
| 5 | `python run.py run` | Main experiment: 5 variants × 40 questions × 3 repeats. Resumable if interrupted. |
| 6 | `python run.py judge` | Grades answers. **Fill the `human_verdict` column in `results/manual_check.csv`.** |
| 7 | `python run.py analyze` | Prints all results; writes `results/` files and `report/results.csv`. Check `results/regressions.csv`. |
| 8 | `python run.py report` | Rebuilds the figures and both PDFs in `report/`. |

To use an API judge instead of a local one, set `JUDGE["backend"] = "openai"`, fill `base_url` and `model`,
and export your key: `export JUDGE_API_KEY=...`.

## Outputs

- `results/runs.jsonl`: every single run (tokens, TTFT, prefill/decode time, answer, citations)
- `results/summary.csv`: one row per variant
- `results/stats.md`: latency per input/output token, exchange rate, regression, McNemar tests, non-inferiority verdicts, judge agreement
- `results/sweep_summary.csv`: the threshold trade-off
- `results/regressions.csv`: answers that got worse than the baseline, with an automatic first label
- `report/*.pdf`: the 3-page submission and the long research-paper version

## Design notes

- **"Document" = one section** of a documentation page (an h2 heading). The baseline retrieves the best-matching
  passages and sends their whole parent sections, as a naive RAG system would.
- **No prompt caching**: a unique request ID at the start of every prompt stops Ollama from reusing a cached
  prefix, so each request measures a full prefill. Prompt caching is discussed but deliberately out of scope.
- Both prompt styles ask for citations and allow "not found", so V0 vs V2 isolates **answer length** only.
- Latency is end-to-end per question, **including retrieval time**, so T1's reranking cost is not hidden.
- Temperature 0 and a fixed seed; answers are graded once (repeat 1), timings are averaged over all repeats.

## Troubleshooting

- **Hugging Face downloads fail or are very slow** (e.g. from mainland China): `export HF_ENDPOINT=https://hf-mirror.com` before running.
- **`Connection refused` on port 11434**: start the Ollama app.
- **Baseline prompts get cut off**: raise `NUM_CTX` in `config.py`.
- **"Thinking" models** (e.g. Qwen3): set `THINK = False` in `config.py`, otherwise hidden reasoning tokens inflate the output count.

## Cleanup (borrowed Mac)

```
ollama rm llama3.1:8b
ollama rm qwen2.5:7b
```
Then quit Ollama, move it from Applications to the Trash, delete `~/.ollama` and `~/.cache/huggingface`, and
delete this project folder (push to GitHub first).

## Use of AI tools

[AI-use statement to be added.]

## Data licence

The knowledge base is the Kubernetes documentation (https://kubernetes.io), © The Kubernetes Authors,
licensed under CC BY 4.0. A dated copy is stored in `data/raw/` for reproducibility.
