"""Map each question to its gold passages, using the source_section column. Review data/gold.csv by hand!"""
import csv
import re


def _words(s: str):
    return set(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def _parts(source_section: str):
    """'Debug Pods > X + Debug Services > Y / Z' -> [['Debug Pods','X'], ['Debug Services','Y'], ['Z']]"""
    out = []
    for chunk in re.split(r"\s\+\s|;|\s/\s", source_section or ""):
        segs = [s.strip() for s in chunk.split(">") if s.strip()]
        if segs:
            out.append(segs)
    return out


def _match(segs, passages):
    """Passages whose path contains the most specific heading of this part (fuzzy word match)."""
    for depth in range(len(segs), 0, -1):
        target = _words(segs[depth - 1])
        hits = [p for p in passages if target and target <= _words(p["path"])]
        if hits:
            return hits
    return []


def build_gold(questions, passages, retriever):
    rows = []
    for q in questions:
        if q["type"] == "unanswerable":
            rows.append({"qid": q["id"], "type": q["type"], "gold_passages": "", "gold_sections": "",
                         "method": "none (unanswerable)", "preview": ""})
            continue
        query = f"{q['question']} {q['reference_answer']}"
        chosen, method = [], "heading match"
        for segs in _parts(q["source_section"]):
            cands = _match(segs, passages)
            if not cands:
                method = "page fallback (CHECK)"
                cands = [p for p in passages if _words(q["source_page"]) <= _words(p["page"] + " " + p["path"])] or passages
            scores = retriever.reranker.score(query, [f"{p['path']}\n{p['text']}" for p in cands])
            best = cands[int(scores.argmax())]
            if best["id"] not in [c["id"] for c in chosen]:
                chosen.append(best)
        if q["type"] == "multi" and len(chosen) < 2:   # make sure multi questions have 2 gold passages
            cands = [p for p in passages if p["id"] not in [c["id"] for c in chosen]]
            scores = retriever.reranker.score(query, [f"{p['path']}\n{p['text']}" for p in cands])
            chosen.append(cands[int(scores.argmax())])
            method += " + best extra (CHECK)"
        rows.append({"qid": q["id"], "type": q["type"],
                     "gold_passages": ";".join(c["id"] for c in chosen),
                     "gold_sections": ";".join(sorted({c["section_id"] for c in chosen})),
                     "method": method,
                     "preview": " || ".join(f"{c['id']}: {c['path']} :: {c['text'][:140]}" for c in chosen)})
    return rows


def save_gold(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def load_gold(path, passages_by_id):
    """Returns {qid: [passage ids]} and {qid: set(section ids)}; section ids are recomputed from passages."""
    gp, gs = {}, {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ids = [x.strip() for x in r["gold_passages"].split(";") if x.strip()]
            gp[r["qid"]] = ids
            gs[r["qid"]] = {passages_by_id[i]["section_id"] for i in ids if i in passages_by_id}
    return gp, gs
