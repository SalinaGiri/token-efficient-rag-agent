"""Turn raw runs + judgements into the numbers, statistics and CSV files used in the report."""
import csv
import random
from math import comb
from statistics import mean

import numpy as np

from .agent import VARIANTS
from .judge import verdict_for


def score_runs(runs, questions_by_id, gold_sections, passages_by_id, cache):
    out = []
    for r in runs:
        v = verdict_for(r, cache)
        unans = questions_by_id[r["qid"]]["type"] == "unanswerable"
        gsec = gold_sections.get(r["qid"], set())
        cit_good = 0
        for cid in r["cited"]:
            sec = cid if cid.startswith("D") else passages_by_id.get(cid, {}).get("section_id")
            cit_good += sec in gsec
        correct = (v == "abstained") if unans else (v == "correct")
        out.append({**r, "verdict": v, "unanswerable": unans, "correct": correct,
                    "cit_total": len(r["cited"]), "cit_good": cit_good,
                    "good": correct if unans else (correct and cit_good > 0)})
    return out


def _pct(xs):
    return 100 * mean(xs) if xs else float("nan")


def summarize(scored, vkey, experiment="main", tau=None):
    rs = [r for r in scored if r["variant"] == vkey and r["experiment"] == experiment
          and (tau is None or r["tau"] == tau)]
    if not rs:
        return None
    first = [r for r in rs if r["repeat"] == 1]
    ans = [r for r in first if not r["unanswerable"]]
    unans = [r for r in first if r["unanswerable"]]
    cited = [r for r in ans if not r["abstained"]]
    llm = [r for r in rs if r["llm_called"]]
    total_tokens = sum(r["prompt_tokens"] + r["output_tokens"] for r in first)
    n_good = sum(r["good"] for r in first)
    return {
        "variant": VARIANTS[vkey]["name"], "key": vkey, "tau": rs[0]["tau"], "n_questions": len(first),
        "input_tokens": mean(r["prompt_tokens"] for r in rs),
        "output_tokens": mean(r["output_tokens"] for r in rs),
        "ttft_s": mean(r["ttft_ms"] for r in rs) / 1000,
        "latency_s": mean(r["latency_ms"] for r in rs) / 1000,
        "retrieval_ms": mean(r["retrieval_ms"] for r in rs),
        "correct_pct": _pct([r["correct"] for r in first]),
        "good_pct": _pct([r["good"] for r in first]),
        "citation_precision_pct": (100 * sum(r["cit_good"] for r in cited) / max(1, sum(r["cit_total"] for r in cited))),
        "abstention_acc_pct": _pct([r["correct"] for r in unans]),
        "false_abstention_pct": _pct([r["abstained"] for r in ans]),
        "truncation_pct": _pct([r["truncated"] for r in llm]),
        "llm_calls_pct": _pct([r["llm_called"] for r in first]),
        "tcca": total_tokens / n_good if n_good else float("inf"),
    }


def mcnemar_exact(a, b):
    """Two-sided exact McNemar test on paired booleans. Returns (b_only, a_only, p)."""
    b_only = sum(1 for x, y in zip(a, b) if not x and y)
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    n = a_only + b_only
    if n == 0:
        return a_only, b_only, 1.0
    k = min(a_only, b_only)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return a_only, b_only, p


def bootstrap_diff(a, b, n=5000, seed=1):
    rng = random.Random(seed)
    idx = list(range(len(a)))
    diffs = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        diffs.append(100 * (mean(b[i] for i in s) - mean(a[i] for i in s)))
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)]


def per_question(scored, vkey, field="correct"):
    rs = sorted([r for r in scored if r["variant"] == vkey and r["experiment"] == "main" and r["repeat"] == 1],
                key=lambda r: r["qid"])
    return [r["qid"] for r in rs], [bool(r[field]) for r in rs]


def latency_model(runs):
    llm = [r for r in runs if r["experiment"] == "main" and r["llm_called"]]
    if not llm:
        return None
    pin = sum(r["prompt_tokens"] for r in llm)
    pout = sum(r["output_tokens"] for r in llm)
    ms_in = sum(r["prefill_ms"] for r in llm) / max(1, pin)
    ms_out = sum(r["decode_ms"] for r in llm) / max(1, pout)
    X = np.array([[1, r["prompt_tokens"], r["output_tokens"]] for r in llm], dtype=float)
    y = np.array([r["llm_wall_ms"] for r in llm], dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = 1 - ((y - pred) ** 2).sum() / max(1e-9, ((y - y.mean()) ** 2).sum())
    return {"ms_per_input_token": ms_in, "ms_per_output_token": ms_out, "exchange_rate": ms_out / ms_in if ms_in else float("nan"),
            "reg_a_ms": coef[0], "reg_b_ms_per_in": coef[1], "reg_c_ms_per_out": coef[2], "reg_r2": r2, "n_calls": len(llm)}


def failure_taxonomy(scored, gold_passages, gold_sections, passages_by_id):
    """Questions correct in V0 but wrong in an optimised variant, with an automatic first label to review."""
    base = {r["qid"]: r for r in scored if r["variant"] == "V0" and r["experiment"] == "main" and r["repeat"] == 1}
    rows = []
    for r in scored:
        if r["experiment"] != "main" or r["repeat"] != 1 or r["variant"] in ("V0", "VO"):
            continue
        b = base.get(r["qid"])
        if not b or not b["correct"] or r["correct"]:
            continue
        if r["abstained"]:
            label = "threshold too strict (false abstention)" if not r["unanswerable"] else "other"
        elif r["truncated"]:
            label = "truncated answer"
        else:
            got = set(r["retrieved"])
            gp, gs = set(gold_passages.get(r["qid"], [])), gold_sections.get(r["qid"], set())
            hit = bool(got & gp) or bool(got & gs) or any(passages_by_id.get(i, {}).get("section_id") in gs for i in got)
            label = "retrieval miss" if (gp and not hit) else "wrong answer despite evidence"
        rows.append({"variant": r["variant"], "qid": r["qid"], "auto_label": label, "your_label": "",
                     "answer": r["answer"][:300]})
    return rows


def judge_agreement(path):
    try:
        with open(path, encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r[list(r.keys())[-1]].strip()]
    except FileNotFoundError:
        return None
    if not rows:
        return None
    last = list(rows[0].keys())[-1]
    agree = sum(r["judge_verdict"].strip().lower() == r[last].strip().lower() for r in rows)
    return agree, len(rows)


def write_csv(rows, path, fields=None):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0].keys()), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
