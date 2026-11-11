"""Offline test of the whole pipeline with fake models (no internet, no Ollama needed).
Run:  python -m tests.test_pipeline"""
import json, re, tempfile, types
from pathlib import Path
import numpy as np

import config
from src import corpus, gold, judge, analyze
from src.agent import VARIANTS, run_loop
from src.llm import LLMResult
from src.retrieval import Retriever

HTML = """<html><body><nav>menu</nav><main>
<h1>Troubleshooting Applications</h1><p>Debugging common containerized application issues.</p>
<div><h1>1 - Debug Pods</h1><p>Intro to debugging pods.</p>
<h2>My pod stays pending</h2><p>If a Pod is stuck in Pending it cannot be scheduled. You may not have enough resources.</p>
<ul><li><p>Delete Pods or add nodes.</p></li><li>hostPort limits scheduling.</li></ul>
<h2>Examining pod logs</h2><p>Look at the logs of the affected container:</p><pre>kubectl logs ${POD_NAME} -c ${CONTAINER_NAME} --previous</pre>
<h3>Crash logs</h3><p>The --previous flag shows the log of the previous container instance after a crash.</p></div>
<div><h1>2 - Debug Services</h1><h2>Does the Service exist?</h2><p>Run kubectl get svc hostnames to check it exists.</p>
<table><tr><th>Status</th><th>Meaning</th></tr><tr><td>Init:1/2</td><td>one of two done</td></tr></table>
<p>Last modified April 09, 2025</p></div></main><footer>footer</footer></body></html>"""

def words(t): return re.findall(r"[a-z0-9]+", t.lower())

class FakeEmbedder:
    name = "fake"
    def encode(self, texts):
        out = []
        for t in texts:
            v = np.zeros(256)
            for w in words(t): v[hash(w) % 256] += 1
            out.append(v / (np.linalg.norm(v) or 1))
        return np.array(out)

class FakeReranker:
    def score(self, q, texts):
        qw = set(words(q))
        return np.array([len(qw & set(words(t))) - 3.0 for t in texts], dtype=float)

class FakeLLM:
    model = "fake"
    def chat(self, system, user, max_tokens, json_mode=False):
        ids = re.findall(r"^\[([DP]\d+)\]", user, re.M)
        text = f"Use kubectl logs --previous [{ids[0]}]." if ids else "I cannot find this in the documentation."
        if "Answer contract" not in system: text += " Extra explanation. " * 20
        n_in, n_out = len(user) // 4, min(max_tokens, len(text) // 4)
        return LLMResult(text, n_in, n_out, 5 + n_in * 0.01, 5 + n_in * 0.01 + n_out * 2, n_in * 0.01, n_out * 2, 0,
                         "length" if n_out >= max_tokens else "stop")

class FakeJudge:
    def chat(self, system, user, max_tokens, json_mode=False):
        ok = "--previous" in user.split("ASSISTANT ANSWER:")[1]
        return LLMResult(json.dumps({"verdict": "correct" if ok else "incorrect", "reason": "fake"}), 0, 0, 0, 0, 0, 0, 0, "stop")

def main():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "a.html").write_text(HTML)
    sections, passages = corpus.build_corpus({"applications": tmp / "a.html"}, 250)
    assert sections and passages, "parsing failed"
    assert not any("Last modified" in s["text"] or "menu" in s["text"] for s in sections)
    assert any("--previous" in p["text"] for p in passages)
    print(f"corpus: {len(sections)} sections, {len(passages)} passages")
    for s in sections: print("  ", s["id"], s["path"], s["tokens"])

    qs = [{"id": "q01", "type": "single", "question": "How do I see logs of a crashed container with --previous?",
           "reference_answer": "kubectl logs --previous", "source_page": "Troubleshooting Applications",
           "source_section": "Debug Pods > Examining pod logs"},
          {"id": "q02", "type": "multi", "question": "Pod pending and logs?", "reference_answer": "not enough resources; kubectl logs --previous",
           "source_page": "Troubleshooting Applications", "source_section": "Debug Pods > My pod stays pending + Debug Pods > Examining pod logs"},
          {"id": "q03", "type": "unanswerable", "question": "How do I upgrade the cluster?", "reference_answer": "NOT IN CORPUS",
           "source_page": "", "source_section": ""}]
    retr = Retriever(sections, passages, FakeEmbedder(), FakeReranker(), tmp / "cache")
    grows = gold.build_gold(qs, passages, retr)
    gold.save_gold(grows, tmp / "gold.csv")
    pid = {p["id"]: p for p in passages}
    gp, gs = gold.load_gold(tmp / "gold.csv", pid)
    print("gold:", gp)
    assert gp["q01"] and len(gp["q02"]) == 2 and gp["q03"] == []

    cfg = types.SimpleNamespace(**{k: getattr(config, k) for k in dir(config) if k.isupper()})
    runs_path = tmp / "runs.jsonl"
    run_loop("main", list(VARIANTS), [0.0], qs, retr, FakeLLM(), gp, cfg, 2, runs_path, log=lambda *a: None)
    run_loop("main", list(VARIANTS), [0.0], qs, retr, FakeLLM(), gp, cfg, 2, runs_path, log=print)  # resume: 0 left
    runs = [json.loads(l) for l in open(runs_path)]
    assert len(runs) == 3 * 5 * 2, len(runs)
    q3 = [r for r in runs if r["qid"] == "q03" and r["variant"] == "V3"][0]
    print("q03/V3 llm_called:", q3["llm_called"], "abstained:", q3["abstained"])

    cache = judge.judge_runs(runs, {q["id"]: q for q in qs}, FakeJudge(), tmp / "judge.jsonl", log=lambda *a: None)
    scored = analyze.score_runs(runs, {q["id"]: q for q in qs}, gs, pid, cache)
    for v in VARIANTS:
        s = analyze.summarize(scored, v)
        print(f"  {s['variant']:<22} in={s['input_tokens']:7.1f} out={s['output_tokens']:6.1f} "
              f"correct={s['correct_pct']:5.1f} good={s['good_pct']:5.1f} cit={s['citation_precision_pct']:5.1f} "
              f"abst={s['abstention_acc_pct']:5.1f} tcca={s['tcca']:.1f}")
    lat = analyze.latency_model(runs)
    print("latency:", {k: round(v, 3) for k, v in lat.items()})
    print("mcnemar:", analyze.mcnemar_exact([True, True, False, True], [True, False, False, False]))
    print("taxonomy:", analyze.failure_taxonomy(scored, gp, gs, pid))
    judge.write_manual_sample(runs, {q["id"]: q for q in qs}, cache, tmp / "manual.csv")

    # --- extra analyses ---
    taus = [-2.0, 0.0, 2.0]
    run_loop("sweep", ["V0", "V1", "V3"], taus, qs, retr, FakeLLM(), gp, cfg, 1, runs_path, log=lambda *a: None)
    runs = [json.loads(l) for l in open(runs_path)]
    cache = judge.judge_runs(runs, {q["id"]: q for q in qs}, FakeJudge(), tmp / "judge.jsonl", log=lambda *a: None)
    scored = analyze.score_runs(runs, {q["id"]: q for q in qs}, gs, pid, cache)
    t, ok = analyze.choose_tau(scored, taus, {"q01", "q02", "q03"})
    assert t in taus, t
    cv = analyze.cross_validated_tau(scored, taus, "V3", 3.0, folds=2, repeats=3)
    assert sum(cv["tau_picks"].values()) == 2 * 3 and 0 <= cv["cv_correct_pct"] <= 100, cv
    print("cv tau:", {k: cv[k] for k in ("tau_in_sample", "in_sample_correct_pct", "cv_correct_pct", "tau_picks")})
    trade = analyze.tradeoff_rows(scored, taus)
    assert len(trade) == 1 + 2 * len(taus) and trade[0]["variant"] == "V0"

    k = analyze.cohens_kappa([("correct", "correct"), ("correct", "incorrect"),
                              ("incorrect", "incorrect"), ("incorrect", "Incorrect ")])
    assert abs(k - 0.5) < 1e-9, k                       # po = 0.75, pe = 0.5 -> 0.5 (worked by hand)
    assert analyze.cohens_kappa([("correct", "correct"), ("abstained", "abstained")]) == 1.0
    (tmp / "manual.csv").write_text("variant,qid,judge_verdict,human_verdict (correct/incorrect/abstained)\n"
                                    "V0,q01,correct,correct\nV0,q02,incorrect,correct\nV1,q01,correct,\n")
    assert analyze.judge_kappa(tmp / "manual.csv")[1] == 2   # empty human verdicts are skipped

    hw = analyze.hardware_limits({"ms_per_output_token": 50.0, "ms_per_input_token": 1.0}, 2e9, 120, 36864,
                                 {"long": {"mean_prompt_tokens": 8000}})
    assert abs(hw["decode_ceiling_tok_s"] - 60) < 1e-9 and abs(hw["bandwidth_utilisation_pct"] - 100 / 3) < 1e-9
    assert hw["decode_ceiling_long_prompt_tok_s"] < hw["decode_ceiling_tok_s"]
    ctx = analyze.decode_by_context(runs, split_tokens=100)
    assert ctx and all(c["ms_per_output_token"] > 0 for c in ctx.values()), ctx
    sp = analyze.scale_projection({"input_tokens": 6000, "output_tokens": 300, "latency_s": 6.0},
                                  {"input_tokens": 1000, "output_tokens": 100, "latency_s": 2.0}, None, 1000, 0.5, 2.0)
    assert sp["input_tokens_saved_per_day"] == 5_000_000 and abs(sp["machine_hours_saved_per_day"] - 4000 / 3600) < 1e-9
    assert abs(sp["api_cost_saved_per_day"] - 2.9) < 1e-9   # (5000*0.5 + 200*2.0) * 1000 / 1e6
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    main()
