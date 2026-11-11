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


# ---------- Extra analyses: tuning bias, judge reliability, hardware limits, scale ----------

def subset_metrics(rows):
    """Correctness, abstention and tokens for a set of first-repeat records (one per question)."""
    ans = [r for r in rows if not r["unanswerable"]]
    unans = [r for r in rows if r["unanswerable"]]
    n_good = sum(r["good"] for r in rows)
    tokens = sum(r["prompt_tokens"] + r["output_tokens"] for r in rows)
    return {"correct_pct": _pct([r["correct"] for r in rows]),
            "abstention_acc_pct": _pct([r["correct"] for r in unans]) if unans else float("nan"),
            "answerable_correct_pct": _pct([r["correct"] for r in ans]) if ans else float("nan"),
            "tcca": tokens / n_good if n_good else float("inf"),
            "tokens": tokens, "n_good": n_good}


def choose_tau(scored, taus, qids, variant="V3", experiment="sweep", margin=3.0):
    """The sweep's selection rule on a subset of questions: the lowest TCCA among thresholds whose correctness
    is at most `margin` points below V0 and whose abstention accuracy is not below V0. If none passes,
    take the most correct threshold (ties: lower TCCA)."""
    first = [r for r in scored if r["experiment"] == experiment and r["repeat"] == 1 and r["qid"] in qids]
    base = subset_metrics([r for r in first if r["variant"] == "V0"])
    cands = []
    for t in taus:
        m = subset_metrics([r for r in first if r["variant"] == variant and r["tau"] == t])
        abst_ok = (m["abstention_acc_pct"] != m["abstention_acc_pct"]          # nan: no unanswerable in subset
                   or m["abstention_acc_pct"] >= base["abstention_acc_pct"])
        passes = m["correct_pct"] >= base["correct_pct"] - margin and abst_ok
        cands.append((t, m, passes))
    ok = [c for c in cands if c[2]]
    if ok:
        return min(ok, key=lambda c: c[1]["tcca"])[0], True
    return max(cands, key=lambda c: (c[1]["correct_pct"], -c[1]["tcca"]))[0], False


def cross_validated_tau(scored, taus, variant="V3", margin=3.0, folds=5, repeats=20, seed=11):
    """Estimate how much choosing TAU on the evaluation questions flatters the result.
    Stratified k-fold (by question type), repeated with different shuffles: every question is scored at a TAU
    that was chosen WITHOUT that question. Compares this held-out estimate with the in-sample one."""
    first = [r for r in scored if r["experiment"] == "sweep" and r["repeat"] == 1]
    by_q = {}
    for r in first:
        by_q.setdefault(r["qid"], r)
    qtypes = {}
    for q, r in by_q.items():
        qtypes.setdefault("unanswerable" if r["unanswerable"] else "answerable", []).append(q)
    all_q = set(by_q)
    tau_all, passed_all = choose_tau(scored, taus, all_q, variant, margin=margin)
    in_sample = subset_metrics([r for r in first if r["variant"] == variant and r["tau"] == tau_all])

    rng = random.Random(seed)
    held_out, picks = [], {}
    for _ in range(repeats):
        fold_of = {}
        for qs in qtypes.values():
            qs = sorted(qs)
            rng.shuffle(qs)
            for i, q in enumerate(qs):
                fold_of[q] = i % folds
        chosen = []
        for k in range(folds):
            test = {q for q in all_q if fold_of[q] == k}
            t, _ = choose_tau(scored, taus, all_q - test, variant, margin=margin)
            picks[t] = picks.get(t, 0) + 1
            chosen += [r for r in first if r["variant"] == variant and r["tau"] == t and r["qid"] in test]
        held_out.append(subset_metrics(chosen))
    cv = {k: mean(m[k] for m in held_out) for k in ("correct_pct", "abstention_acc_pct", "tcca")}
    return {"variant": variant, "tau_in_sample": tau_all, "in_sample_passes": passed_all,
            "in_sample_correct_pct": in_sample["correct_pct"], "cv_correct_pct": cv["correct_pct"],
            "in_sample_abstention_pct": in_sample["abstention_acc_pct"], "cv_abstention_pct": cv["abstention_acc_pct"],
            "in_sample_tcca": in_sample["tcca"], "cv_tcca": cv["tcca"],
            "optimism_points": in_sample["correct_pct"] - cv["correct_pct"],
            "tau_picks": dict(sorted(picks.items())), "folds": folds, "repeats": repeats}


def tradeoff_rows(scored, taus, variants=("V1", "V3")):
    """One row per (variant, TAU) from the sweep, plus V0, for the tokens-vs-correctness curve."""
    first = [r for r in scored if r["experiment"] == "sweep" and r["repeat"] == 1]
    rows = []
    base = [r for r in first if r["variant"] == "V0"]
    if base:
        m = subset_metrics(base)
        rows.append({"variant": "V0", "tau": "", "tokens_per_query": m["tokens"] / len(base),
                     "correct_pct": m["correct_pct"], "abstention_acc_pct": m["abstention_acc_pct"], "tcca": m["tcca"]})
    for v in variants:
        for t in taus:
            rs = [r for r in first if r["variant"] == v and r["tau"] == t]
            if rs:
                m = subset_metrics(rs)
                rows.append({"variant": v, "tau": t, "tokens_per_query": m["tokens"] / len(rs),
                             "correct_pct": m["correct_pct"], "abstention_acc_pct": m["abstention_acc_pct"],
                             "tcca": m["tcca"]})
    return rows


def _norm_verdict(s):
    s = (s or "").strip().lower()
    return {"right": "correct", "wrong": "incorrect", "abstain": "abstained"}.get(s, s)


def cohens_kappa(pairs):
    """Agreement between two raters beyond chance. pairs = [(rater_a, rater_b), ...]. 1 = perfect, 0 = chance."""
    pairs = [(_norm_verdict(a), _norm_verdict(b)) for a, b in pairs]
    n = len(pairs)
    if n == 0:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def judge_kappa(path):
    """Cohen's kappa between the judge and the manual grades in results/manual_check.csv (filled rows only)."""
    try:
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return None
    if not rows:
        return None
    last = list(rows[0].keys())[-1]
    pairs = [(r["judge_verdict"], r[last]) for r in rows if (r[last] or "").strip()]
    return (cohens_kappa(pairs), len(pairs)) if pairs else None


def decode_by_context(runs, split_tokens=2000):
    """Decode speed for short vs long prompts. Each output token reads the weights AND the KV cache of all
    previous tokens, so long prompts make every output token slower."""
    llm = [r for r in runs if r["experiment"] == "main" and r["llm_called"] and r["output_tokens"] > 1]
    out = {}
    for name, rs in (("short", [r for r in llm if r["prompt_tokens"] < split_tokens]),
                     ("long", [r for r in llm if r["prompt_tokens"] >= split_tokens])):
        if rs:
            out[name] = {"n": len(rs), "mean_prompt_tokens": mean(r["prompt_tokens"] for r in rs),
                         "ms_per_output_token": sum(r["decode_ms"] for r in rs) / sum(r["output_tokens"] for r in rs)}
    return out


def hardware_limits(lat, model_bytes, bandwidth_gb_s, kv_bytes_per_token=None, by_context=None):
    """Compare measured decode speed with the memory-bandwidth ceiling: every output token must read all
    weights once, so tokens/s <= bandwidth / model size."""
    if not lat or not model_bytes or not bandwidth_gb_s:
        return None
    ceiling = bandwidth_gb_s * 1e9 / model_bytes
    measured = 1000 / lat["ms_per_output_token"]
    res = {"model_gb": model_bytes / 1e9, "bandwidth_gb_s": bandwidth_gb_s,
           "decode_ceiling_tok_s": ceiling, "decode_measured_tok_s": measured,
           "bandwidth_utilisation_pct": 100 * measured / ceiling,
           "prefill_measured_tok_s": 1000 / lat["ms_per_input_token"]}
    if kv_bytes_per_token and by_context and "long" in by_context:
        kv = kv_bytes_per_token * by_context["long"]["mean_prompt_tokens"]
        res["kv_bytes_per_token"] = kv_bytes_per_token
        res["kv_cache_gb_long_prompt"] = kv / 1e9
        res["decode_ceiling_long_prompt_tok_s"] = bandwidth_gb_s * 1e9 / (model_bytes + kv)
    return res


def scale_projection(base, opt, lat, queries_per_day, price_in_per_m=None, price_out_per_m=None):
    """What the measured per-query savings mean at a given daily volume. Uses only measured averages;
    API cost only if prices are given."""
    d_in = base["input_tokens"] - opt["input_tokens"]
    d_out = base["output_tokens"] - opt["output_tokens"]
    res = {"queries_per_day": queries_per_day,
           "input_tokens_saved_per_day": d_in * queries_per_day,
           "output_tokens_saved_per_day": d_out * queries_per_day,
           "latency_saved_s_per_query": base["latency_s"] - opt["latency_s"],
           "machine_hours_saved_per_day": (base["latency_s"] - opt["latency_s"]) * queries_per_day / 3600}
    if price_in_per_m is not None and price_out_per_m is not None:
        res["api_cost_saved_per_day"] = (d_in * price_in_per_m + d_out * price_out_per_m) * queries_per_day / 1e6
    return res
