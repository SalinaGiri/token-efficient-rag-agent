# Fewer, Better Tokens

**Can a documentation chatbot use far fewer tokens and still give correct, cited answers?**
This project measures exactly that, on a real laptop, with a real local model.

📄 **The 3-page report:** [`report/Fewer_Better_Tokens_3page.pdf`](report/Fewer_Better_Tokens_3page.pdf)
(3 pages of text, then references and Appendix A: a one-page record of every run, check and number.)

Technical exercise for internship 2026-INT-298 (*Token-Efficient AI-Agent Design for an Operational Knowledge Hub*).

---

## The short version

A chatbot answers 40 questions about the Kubernetes troubleshooting documentation. It looks up relevant text
first (retrieval) and then lets a language model write the answer (this is called **RAG**,
retrieval-augmented generation). I compared a normal version with versions that try to save tokens, and checked
whether the answers stayed correct.

**Main finding:** sending the model only the few passages that really match the question cut input tokens by
about 90% and made answers about 6 times faster (26 s to 4 s), with no loss of correctness. Forcing short
answers saved tokens too, but the answers lost important details, so that idea did not pass.

## Why two techniques?

A language model works in two phases, and each costs time in a different way:

| Phase | What happens | What it costs |
|---|---|---|
| **Prefill** (reading) | The model reads the whole prompt at once | Cheap per token, but prompts can be long |
| **Decode** (writing) | The model writes the answer one token at a time | Expensive per token |

So I tested one technique for each phase:

- **T1, adaptive retrieval (less to read).** Find 20 candidate passages, score them with a second, more precise
  model (a *reranker*), and keep only the ones scoring at least `TAU` (at most 4). If nothing scores high
  enough, the bot says "not found" **without calling the model at all**.
- **T4, output budget (less to write).** Ask for the answer first, in at most 3 sentences, with citations,
  and stop after 150 tokens.

## The five versions compared

| Version | What it reads | How it answers |
|---|---|---|
| **V0** Baseline | the 10 best-matching sections, in full | free length |
| **V1** | T1: only the best passages | free length |
| **V2** | the 10 best-matching sections, in full | T4: short |
| **V3** Optimised | T1: only the best passages | T4: short |
| **VO** Oracle | only the correct passages (a "perfect retrieval" upper bound) | T4: short |

## Results

Main run: 40 questions × 5 versions × 3 repeats = 600 answers, plus 520 runs to choose `TAU`.
Model: Qwen2.5-3B-Instruct, run locally with Ollama on an Apple M4 MacBook Air.

<!-- results:start -->
| Variant | Input tokens | Output tokens | Latency (s) | Correct (%) | Abstain (%) | TPCA | vs V0 (points, p) |
|---|---:|---:|---:|---:|---:|---:|---|
| V0 Baseline | 6,487 | 133 | 26.1 | 88 | 71 | 7,573 |  |
| V1 Adaptive retrieval | 599 | 71 | 4.0 | 92 | 100 | 721 | +5.0, p = 0.73 ✓ |
| V2 Output budget | 6,556 | 59 | 23.8 | 70 | 43 | 9,446 | -17.5, p = 0.04 |
| V3 Optimised | 658 | 36 | 3.2 | 78 | 100 | 896 | -10.0, p = 0.34 |
| VO Oracle | 368 | 33 | 2.0 | 82 | 100 | 486 | -5.0, p = 0.75 |

- 1 output token costs about **8 input tokens** of latency on the Apple M4; decode runs at 65% of the memory-bandwidth ceiling (57 tokens/s).
- LLM judge vs blind manual grading: 31/33 agree, Cohen's kappa = 0.84.
- TAU = 0; cross-validation shows tuning on the test questions is optimistic by up to 7 points.
- ✓ = passes the non-inferiority rule (at most 3 points less correct, no drop in abstention). Full results: `results/stats.md`; report: `report/Fewer_Better_Tokens_3page.pdf`.
<!-- results:end -->

**How to read the table**

- **Input / output tokens:** average tokens per question that the model read and wrote.
- **Latency:** average seconds from question to finished answer (retrieval time included).
- **Correct:** share of answers graded correct.
- **Abstain:** for the 7 questions the documentation cannot answer, how often the bot correctly said "not found".
- **TPCA:** tokens per correct answer, lower is better. It shows how much you pay for one useful answer.
- **vs V0:** change in correctness compared with the baseline, and the p-value of a McNemar test (a test for
  paired yes/no results). p below 0.05 means the difference is unlikely to be chance.
- **✓:** passes the rule I fixed *before* running: at most 3 points less correct and no worse at saying "not found".

## How I checked the results can be trusted

All of these run from the saved measurements, without extra model calls (`python run.py analyze`):

- **Is the grader reliable?** An AI judge (DeepSeek, a different model family) graded every answer. I graded
  33 answers myself without seeing its verdict. We agreed on 31 of 33 (Cohen's kappa 0.84, where 1 is perfect
  agreement and 0 is chance).
- **Did I tune on the test questions?** `TAU` was picked on the same 40 questions. Cross-validation (choosing
  `TAU` on some questions and testing on the others, 100 times) shows how much this flatters the result.
- **Do the speeds make physical sense?** Writing each token needs the whole model read from memory once, so the
  M4's memory speed sets a maximum. The measured speed reached 65% of it.
- **What would it mean at scale?** The measured savings per question, projected to 100,000 questions a day.

## What is in this repository

```
report/                 the 3-page report (PDF), its figures and the scripts that build them
results/                every measurement: all runs, judge verdicts, my manual grades, statistics
data/questions.csv      the 40 test questions (25 single-fact, 8 two-part, 7 not answerable)
data/gold.csv           the correct passages for each question, checked by hand
data/raw/               a dated copy of the documentation, so results can be reproduced
src/                    the chatbot and the evaluation code (see below)
config.py               all settings in one place (model, TAU, repeats, ...)
run.py                  one command for every step
```

Inside `src/`: `corpus.py` downloads and splits the documentation, `retrieval.py` finds and reranks passages,
`llm.py` talks to Ollama and measures reading and writing time separately, `prompts.py` holds the prompts,
`agent.py` runs the five versions, `judge.py` grades answers, `analyze.py` computes all statistics.

## Run it yourself (macOS, Apple Silicon)

**1. Install** [Ollama](https://ollama.com) and Python 3.11 or newer, then get the model:
```
ollama pull modelscope.cn/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
```
(I pulled it from ModelScope because the Ollama registry was unreachable from my network.)

**2. Set up Python** inside the project folder:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Run the steps in order.** Keep the Mac plugged in and close heavy apps while measuring.

| Step | Command | What it does |
|---|---|---|
| 1 | `python run.py fetch` | Downloads the documentation and splits it into passages |
| 2 | `python run.py gold` | Suggests the correct passage per question; **check `data/gold.csv` by hand** |
| 3 | `python run.py scores` | Shows reranker score ranges, to choose sensible `TAU` values |
| 4 | `python run.py sweep` | Tries each `TAU`; put the chosen one in `config.py` |
| 5 | `python run.py run` | The main experiment (600 answers). Can be stopped and resumed |
| 6 | `python run.py judge` | Grades the answers; then **fill `human_verdict` in `results/manual_check.csv`** |
| 7 | `python run.py analyze` | Computes all results and statistics |
| 8 | `python run.py report` | Rebuilds the figures, the PDF and the results table in this README |

**The judge's API key** is never saved in the project. Type it in only for the session that needs it:
```
read -rs "JUDGE_API_KEY?API key: "; export JUDGE_API_KEY; echo
```
(That is zsh, the macOS default. In bash: `read -rsp "API key: " JUDGE_API_KEY; export JUDGE_API_KEY`.)
To grade with a local model instead, set `JUDGE["backend"] = "ollama"` in `config.py`.

## Design choices worth knowing

- **Fair baseline.** V0 sends whole documentation sections, as a simple RAG system would.
- **No prompt caching.** Every prompt starts with a unique ID, so Ollama cannot reuse earlier work and each
  timing is a full, honest measurement.
- **One change at a time.** Both prompt styles ask for citations and allow "not found", so V0 vs V2 only
  changes the answer length.
- **Honest latency.** Retrieval and reranking time are included, so T1's own cost is not hidden.
- **Repeatable.** Temperature 0 and a fixed seed. Answers are graded once; timings are averaged over 3 repeats.
- **Cool laptop.** The MacBook Air has no fan, so the run pauses 2 minutes every 50 answers (never during a
  timed answer).

## Troubleshooting

- **Hugging Face downloads fail or are slow:** run `export HF_ENDPOINT=https://hf-mirror.com` first.
- **`Connection refused` on port 11434:** start the Ollama app.
- **Long prompts get cut off:** raise `NUM_CTX` in `config.py`.
- **"Thinking" models (e.g. Qwen3):** set `THINK = False` in `config.py`, or hidden reasoning inflates the token counts.

## Cleanup

```
ollama rm modelscope.cn/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
```
To remove everything: quit Ollama, delete `~/.ollama` and `~/.cache/huggingface`, and delete this folder
(the Python environment lives inside it).

## Use of AI tools

Claude Code (Anthropic) was used to speed up coding of the RAG pipeline and to help generate scripts (evaluation, figures and report build), and to set up Ollama. The architecture and framework, the literature research on effective token-reduction methods, the choice of what to test, the test questions, the blind manual grading of answers and the analysis of the results are my own work.

## Data licence

The knowledge base is the Kubernetes documentation (https://kubernetes.io), © The Kubernetes Authors,
licensed under CC BY 4.0. A dated copy is stored in `data/raw/` for reproducibility.
