"""Grade answers with a judge model; create a sample for checking the judge by hand."""
import csv
import hashlib
import json
import random
from pathlib import Path

from . import prompts


def _key(qid, answer):
    return hashlib.sha1(f"{qid}\n{answer}".encode()).hexdigest()


def _parse(text: str) -> dict:
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        d = json.loads(text[start:end])
        v = str(d.get("verdict", "")).lower().strip()
        if v in ("correct", "incorrect", "abstained"):
            return {"verdict": v, "reason": d.get("reason", "")}
    except (ValueError, json.JSONDecodeError):
        pass
    low = text.lower()
    for v in ("abstained", "incorrect", "correct"):
        if v in low:
            return {"verdict": v, "reason": "parsed from text: " + text[:200]}
    return {"verdict": "incorrect", "reason": "unparseable judge output: " + text[:200]}


def judge_runs(runs, questions_by_id, client, cache_path: Path, log=print):
    """Judge repeat-1 answers (temperature 0 makes repeats identical). Cached, so re-running is cheap."""
    cache = {}
    if cache_path.exists():
        for line in open(cache_path, encoding="utf-8"):
            r = json.loads(line)
            cache[r["key"]] = r
    todo = [r for r in runs if r["repeat"] == 1 and _key(r["qid"], r["answer"]) not in cache]
    log(f"judge: {len(todo)} new answers to grade ({len(cache)} cached)")
    with open(cache_path, "a", encoding="utf-8") as f:
        for n, r in enumerate(todo, 1):
            k = _key(r["qid"], r["answer"])
            if k in cache:
                continue
            if r["abstained"]:
                out = {"verdict": "abstained", "reason": "abstention phrase or no relevant passage (rule-based)"}
            else:
                q = questions_by_id[r["qid"]]
                res = client.chat(prompts.JUDGE_SYSTEM, prompts.judge_user(q["question"], q["reference_answer"],
                                                                           r["answer"]), 200, json_mode=True)
                out = _parse(res.text)
            row = {"key": k, "qid": r["qid"], **out}
            cache[k] = row
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if n % 20 == 0:
                log(f"  graded {n}/{len(todo)}")
    return cache


def verdict_for(run, cache):
    return cache.get(_key(run["qid"], run["answer"]), {}).get("verdict")


def write_manual_sample(runs, questions_by_id, cache, path: Path, share=0.2, seed=7):
    """Random 20% of LLM-graded answers, for you to grade by hand (fill the human_verdict column)."""
    if path.exists():
        return False
    graded = [r for r in runs if r["repeat"] == 1 and r["llm_called"] and not r["abstained"]
              and r["experiment"] == "main"]
    random.Random(seed).shuffle(graded)
    sample = graded[: max(1, round(len(graded) * share))]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variant", "qid", "question", "reference_answer", "assistant_answer", "judge_verdict",
                    "human_verdict (correct/incorrect/abstained)"])
        for r in sample:
            q = questions_by_id[r["qid"]]
            w.writerow([r["variant"], r["qid"], q["question"], q["reference_answer"], r["answer"],
                        verdict_for(r, cache), ""])
    return True
