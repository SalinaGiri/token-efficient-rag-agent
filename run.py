"""One entry point for the whole experiment.

    python run.py fetch      download the docs once and split them into sections and passages
    python run.py gold       map questions to gold passages  -> review data/gold.csv
    python run.py scores     show reranker scores, to choose the TAU_SWEEP range
    python run.py sweep      try every threshold in TAU_SWEEP (1 repeat) and suggest the best TAU
    python run.py run        main experiment: all 5 variants x 40 questions x REPEATS
    python run.py judge      grade the answers and create results/manual_check.csv
    python run.py analyze    compute all metrics and statistics, write report/results.csv
    python run.py report     rebuild the figures and both PDF reports
"""
import argparse
import csv
import json
import subprocess
import sys
from statistics import median

import config as cfg
from src import corpus, gold as goldmod, judge as judgemod, analyze as an
from src.agent import VARIANTS, run_loop, warm_up

RUNS = cfg.RESULTS / "runs.jsonl"
JUDGE_CACHE = cfg.RESULTS / "judgements.jsonl"
MANUAL = cfg.RESULTS / "manual_check.csv"


def load_questions():
    with open(cfg.DATA / "questions.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_corpus():
    s, p = cfg.DATA / "sections.jsonl", cfg.DATA / "passages.jsonl"
    if not p.exists():
        sys.exit("Run `python run.py fetch` first.")
    return corpus.load_jsonl(s), corpus.load_jsonl(p)


def make_retriever(sections, passages):
    from src.retrieval import Embedder, Reranker, Retriever
    return Retriever(sections, passages, Embedder(cfg.EMBED_MODEL), Reranker(cfg.RERANK_MODEL), cfg.DATA / "cache")


def make_llm():
    from src.llm import OllamaClient
    return OllamaClient(cfg.OLLAMA_URL, cfg.LLM_MODEL, cfg.NUM_CTX, cfg.SEED, cfg.TEMPERATURE, cfg.THINK)


def load_runs():
    if not RUNS.exists():
        return []
    return [json.loads(l) for l in open(RUNS, encoding="utf-8") if l.strip()]


def cmd_fetch(a):
    files = corpus.fetch(cfg.CORPUS_URLS, cfg.DATA / "raw", refresh=a.refresh)
    sections, passages = corpus.build_corpus(files, cfg.PASSAGE_TOKENS)
    corpus.save_jsonl(sections, cfg.DATA / "sections.jsonl")
    corpus.save_jsonl(passages, cfg.DATA / "passages.jsonl")
    info = {"files": {k: str(v.name) for k, v in files.items()}, "urls": cfg.CORPUS_URLS,
            "sections": len(sections), "passages": len(passages),
            "approx_tokens_total": sum(s["tokens"] for s in sections),
            "median_section_tokens": median(s["tokens"] for s in sections),
            "median_passage_tokens": median(p["tokens"] for p in passages)}
    (cfg.DATA / "corpus_info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


def cmd_gold(a):
    path = cfg.DATA / "gold.csv"
    if path.exists() and not a.force:
        sys.exit("data/gold.csv already exists (your reviewed version is kept). Use --force to rebuild it.")
    sections, passages = load_corpus()
    rows = goldmod.build_gold(load_questions(), passages, make_retriever(sections, passages))
    goldmod.save_gold(rows, path)
    print(f"Wrote {path}. Open it and check every row; rows marked CHECK need attention.")


def cmd_scores(a):
    sections, passages = load_corpus()
    r = make_retriever(sections, passages)
    by_type = {}
    for q in load_questions():
        s = r.top_rerank_score(q["question"], cfg.CANDIDATES)
        by_type.setdefault(q["type"], []).append(s)
        print(f"{q['id']} {q['type']:<13} top score {s:7.2f}")
    for t, xs in by_type.items():
        xs = sorted(xs)
        print(f"{t:<13} min {xs[0]:.2f}  median {median(xs):.2f}  max {xs[-1]:.2f}")
    print("Choose TAU_SWEEP values between the unanswerable and answerable score ranges.")


def _gold_passages(passages):
    path = cfg.DATA / "gold.csv"
    if not path.exists():
        sys.exit("Run `python run.py gold` first (needed for the oracle and citation scoring).")
    return goldmod.load_gold(path, {p["id"]: p for p in passages})


def cmd_sweep(a):
    sections, passages = load_corpus()
    gp, _ = _gold_passages(passages)
    retr, llm = make_retriever(sections, passages), make_llm()
    warm_up(llm)
    run_loop("sweep", ["V0", "V1", "V3"], cfg.TAU_SWEEP, load_questions(), retr, llm, gp, cfg, 1, RUNS)
    cmd_judge(a, only_sweep=True)
    scored = _scored(passages)
    base = an.summarize(scored, "V0", "sweep")
    rows = [base] + [an.summarize(scored, v, "sweep", t) for t in cfg.TAU_SWEEP for v in ("V1", "V3")]
    rows = [r for r in rows if r]
    an.write_csv(rows, cfg.RESULTS / "sweep_summary.csv")
    _print_table(rows)
    ok = [r for r in rows if r["key"] == "V3" and r["correct_pct"] >= base["correct_pct"] - cfg.NONINFERIORITY_POINTS
          and r["abstention_acc_pct"] >= base["abstention_acc_pct"]]
    if ok:
        best = min(ok, key=lambda r: r["tcca"])
        print(f"\nSuggested TAU = {best['tau']} (lowest TCCA that passes the non-inferiority rule). Set it in config.py.")
    else:
        print("\nNo threshold passes the non-inferiority rule; report this honestly and pick the best trade-off.")


def cmd_run(a):
    sections, passages = load_corpus()
    gp, _ = _gold_passages(passages)
    retr, llm = make_retriever(sections, passages), make_llm()
    warm_up(llm)
    run_loop("main", list(VARIANTS), [cfg.TAU], load_questions(), retr, llm, gp, cfg, cfg.REPEATS, RUNS)


def cmd_judge(a, only_sweep=False):
    from src.llm import make_judge_client
    qs = {q["id"]: q for q in load_questions()}
    runs = [r for r in load_runs() if not only_sweep or r["experiment"] == "sweep"]
    client = make_judge_client(cfg.JUDGE, cfg.OLLAMA_URL, 8192)
    cache = judgemod.judge_runs(runs, qs, client, JUDGE_CACHE)
    if not only_sweep and judgemod.write_manual_sample(runs, qs, cache, MANUAL):
        print(f"Wrote {MANUAL}: grade these answers yourself (human_verdict column) to check the judge.")


def _scored(passages):
    qs = {q["id"]: q for q in load_questions()}
    _, gs = _gold_passages(passages)
    cache = {}
    if JUDGE_CACHE.exists():
        for l in open(JUDGE_CACHE, encoding="utf-8"):
            r = json.loads(l)
            cache[r["key"]] = r
    return an.score_runs(load_runs(), qs, gs, {p["id"]: p for p in passages}, cache)


def _print_table(rows):
    cols = ["variant", "tau", "input_tokens", "output_tokens", "ttft_s", "latency_s", "correct_pct", "good_pct",
            "citation_precision_pct", "abstention_acc_pct", "false_abstention_pct", "tcca"]
    print(" | ".join(cols))
    for r in rows:
        print(" | ".join(f"{r[c]:.2f}" if isinstance(r[c], float) else str(r[c]) for c in cols))


def cmd_analyze(a):
    sections, passages = load_corpus()
    pid = {p["id"]: p for p in passages}
    gp, gs = _gold_passages(passages)
    keep = lambda r: r["experiment"] != "main" or r["tau"] in (None, cfg.TAU)   # main runs at the chosen TAU
    scored = [r for r in _scored(passages) if keep(r)]
    if any(r["verdict"] is None for r in scored if r["repeat"] == 1 and r["experiment"] == "main"):
        sys.exit("Some answers are not graded yet. Run `python run.py judge` first.")
    rows = [an.summarize(scored, v) for v in VARIANTS]
    rows = [r for r in rows if r]
    an.write_csv(rows, cfg.RESULTS / "summary.csv")
    _print_table(rows)

    lat = an.latency_model([r for r in load_runs() if keep(r)])
    lines = ["# Statistics", ""]
    if lat:
        lines += [f"Latency per input token (prefill): {lat['ms_per_input_token']:.3f} ms",
                  f"Latency per output token (decode): {lat['ms_per_output_token']:.2f} ms",
                  f"Exchange rate: 1 output token = {lat['exchange_rate']:.0f} input tokens in latency",
                  f"Regression on LLM wall time: a = {lat['reg_a_ms']:.1f} ms, b = {lat['reg_b_ms_per_in']:.4f} ms/input token, "
                  f"c = {lat['reg_c_ms_per_out']:.2f} ms/output token, R^2 = {lat['reg_r2']:.3f} (n = {lat['n_calls']})", ""]
        an.write_csv([{"ms_per_input_token": round(lat["ms_per_input_token"], 4),
                       "ms_per_output_token": round(lat["ms_per_output_token"], 3), "placeholder": "no"}],
                     cfg.REPORT / "latency_fit.csv")
    _, base = an.per_question(scored, "V0")
    base_sum = next(r for r in rows if r["key"] == "V0")
    for v in ("V1", "V2", "V3", "VO"):
        qids, other = an.per_question(scored, v)
        if len(other) != len(base):
            continue
        a_only, b_only, p = an.mcnemar_exact(base, other)
        lo, hi = an.bootstrap_diff(base, other)
        s = next(r for r in rows if r["key"] == v)
        diff = s["correct_pct"] - base_sum["correct_pct"]
        passes = diff >= -cfg.NONINFERIORITY_POINTS and s["abstention_acc_pct"] >= base_sum["abstention_acc_pct"]
        lines.append(f"{v} vs V0: correctness {diff:+.1f} points (95% bootstrap CI {lo:+.1f} to {hi:+.1f}); "
                     f"only V0 correct: {a_only}, only {v} correct: {b_only}, McNemar exact p = {p:.3f}; "
                     f"non-inferiority rule: {'PASS' if passes else 'FAIL'}")
    agr = an.judge_agreement(MANUAL)
    if agr:
        lines += ["", f"Judge agreement with your manual grades: {agr[0]}/{agr[1]} ({100 * agr[0] / agr[1]:.0f}%)"]
    (cfg.RESULTS / "stats.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    tax = an.failure_taxonomy(scored, gp, gs, pid)
    an.write_csv(tax, cfg.RESULTS / "regressions.csv")
    print(f"\n{len(tax)} regressions written to results/regressions.csv (check the auto_label column).")

    an.write_csv([{**r, "input_tokens": round(r["input_tokens"]), "output_tokens": round(r["output_tokens"]),
                   "ttft_s": round(r["ttft_s"], 2), "latency_s": round(r["latency_s"], 2),
                   "correct_pct": round(r["correct_pct"]), "good_pct": round(r["good_pct"]),
                   "citation_precision_pct": round(r["citation_precision_pct"]),
                   "abstention_acc_pct": round(r["abstention_acc_pct"]), "tcca": round(r["tcca"]), "placeholder": "no"}
                  for r in rows], cfg.REPORT / "results.csv",
                 ["variant", "input_tokens", "output_tokens", "ttft_s", "latency_s", "correct_pct", "good_pct",
                  "citation_precision_pct", "abstention_acc_pct", "tcca", "placeholder"])
    print("Wrote report/results.csv and report/latency_fit.csv. Next: python run.py report")


def cmd_report(a):
    for script in ("make_figures.py", "build_paper_3page.py", "build_paper.py"):
        subprocess.run([sys.executable, script], cwd=cfg.REPORT, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["fetch", "gold", "scores", "sweep", "run", "judge", "analyze", "report"])
    ap.add_argument("--refresh", action="store_true", help="fetch: download the docs again")
    ap.add_argument("--force", action="store_true", help="gold: overwrite data/gold.csv")
    a = ap.parse_args()
    cfg.RESULTS.mkdir(exist_ok=True)
    globals()[f"cmd_{a.command}"](a)


if __name__ == "__main__":
    main()
