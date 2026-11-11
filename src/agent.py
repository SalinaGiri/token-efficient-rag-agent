"""The chatbot: retrieval + prompt + LLM call, in five variants, plus the experiment loop."""
import json
import re
import time
import uuid
from pathlib import Path

from . import prompts

VARIANTS = {
    "V0": {"name": "V0 Baseline", "retrieval": "baseline", "budget": False},
    "V1": {"name": "V1 Adaptive retrieval", "retrieval": "adaptive", "budget": False},
    "V2": {"name": "V2 Output budget", "retrieval": "baseline", "budget": True},
    "V3": {"name": "V3 Optimised", "retrieval": "adaptive", "budget": True},
    "VO": {"name": "VO Oracle", "retrieval": "oracle", "budget": True},
}
ID_RE = re.compile(r"\b([DP]\d{3,4})\b")


def cited_ids(answer: str):
    seen = []
    for m in ID_RE.findall(answer):
        if m not in seen:
            seen.append(m)
    return seen


def is_abstention(answer: str, abstain_text: str) -> bool:
    a = answer.lower()
    return abstain_text.lower().rstrip(".") in a or "cannot find this in the documentation" in a


def answer_question(vkey, q, retriever, llm, gold_passages, cfg, tau):
    """Run one question through one variant and return a measurement record."""
    v = VARIANTS[vkey]
    t0 = time.perf_counter()
    info = {}
    if v["retrieval"] == "baseline":
        items, retr_ms, info = retriever.baseline_sections(q["question"], cfg.BASELINE_K)
    elif v["retrieval"] == "adaptive":
        items, retr_ms, info = retriever.adaptive_passages(q["question"], tau, cfg.CANDIDATES, cfg.KMAX)
    else:
        items, retr_ms = retriever.items_for(gold_passages.get(q["id"], [])), 0.0
    rec = {"variant": vkey, "qid": q["id"], "qtype": q["type"], "tau": tau if v["retrieval"] == "adaptive" else None,
           "retrieved": [it["id"] for it in items], "retrieval_ms": retr_ms, "retrieval_info": info,
           "context_chars": sum(len(it["text"]) for it in items)}
    if not items:
        # T1: nothing relevant enough -> answer "not found" WITHOUT calling the LLM (zero tokens)
        total = (time.perf_counter() - t0) * 1000
        rec.update({"answer": cfg.ABSTAIN_TEXT, "llm_called": False, "prompt_tokens": 0, "output_tokens": 0,
                    "ttft_ms": total, "latency_ms": total, "llm_ttft_ms": 0, "llm_wall_ms": 0, "prefill_ms": 0,
                    "decode_ms": 0, "load_ms": 0, "truncated": False})
    else:
        system = (prompts.system_budget if v["budget"] else prompts.system_free)(cfg.ABSTAIN_TEXT)
        system = prompts.with_nonce(system, uuid.uuid4().hex[:8])
        max_tokens = cfg.BUDGET_MAX_TOKENS if v["budget"] else cfg.FREE_MAX_TOKENS
        res = llm.chat(system, prompts.build_user(items, q["question"]), max_tokens)
        rec.update({"answer": res.text, "llm_called": True, "prompt_tokens": res.prompt_tokens,
                    "output_tokens": res.output_tokens, "ttft_ms": retr_ms + res.ttft_ms,
                    "latency_ms": (time.perf_counter() - t0) * 1000, "llm_ttft_ms": res.ttft_ms,
                    "llm_wall_ms": res.wall_ms, "prefill_ms": res.prefill_ms, "decode_ms": res.decode_ms,
                    "load_ms": res.load_ms, "truncated": res.done_reason == "length"})
    rec["cited"] = cited_ids(rec["answer"])
    rec["abstained"] = is_abstention(rec["answer"], cfg.ABSTAIN_TEXT)
    return rec


def run_loop(experiment, variants, taus, questions, retriever, llm, gold_passages, cfg, repeats, out_path: Path,
             log=print):
    """Interleave variants per question (reduces drift), append every record to a JSONL file, resume if stopped."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            r = json.loads(line)
            done.add((r["experiment"], r["variant"], r["qid"], r["tau"], r["repeat"]))
    jobs = []
    for rep in range(1, repeats + 1):
        for q in questions:
            for vk in variants:
                for tau in (taus if VARIANTS[vk]["retrieval"] == "adaptive" else [None]):
                    if (experiment, vk, q["id"], tau, rep) not in done:
                        jobs.append((rep, q, vk, tau))
    log(f"{experiment}: {len(jobs)} runs to do ({len(done)} already done)")
    with open(out_path, "a", encoding="utf-8") as f:
        for n, (rep, q, vk, tau) in enumerate(jobs, 1):
            rec = answer_question(vk, q, retriever, llm, gold_passages, cfg, tau)
            rec.update({"experiment": experiment, "repeat": rep, "model": getattr(llm, "model", "")})
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if n % 10 == 0 or n == len(jobs):
                log(f"  {n}/{len(jobs)}  last: {vk} {q['id']} in={rec['prompt_tokens']} out={rec['output_tokens']} "
                    f"{rec['latency_ms']:.0f} ms")
            every, pause = getattr(cfg, "COOLDOWN_EVERY", 0), getattr(cfg, "COOLDOWN_S", 0)
            if every and pause and n % every == 0 and n < len(jobs):
                # Cooling break BETWEEN runs (fanless laptop): no run is timed while paused.
                log(f"  cooling break: {pause} s")
                time.sleep(pause)


def warm_up(llm, log=print):
    """Load the model into memory before measuring, so load time does not distort the first runs."""
    for _ in range(2):
        r = llm.chat("You are a test.", "Say OK.", 5)
    log(f"warm-up done (load {r.load_ms:.0f} ms)")
