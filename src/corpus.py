"""Download the documentation once, then split it into sections ("documents") and passages."""
import json
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

BLOCK_TAGS = ["p", "pre", "li", "table", "dd", "dt", "blockquote"]
HEAD_TAGS = ["h1", "h2", "h3", "h4"]
SKIP_PREFIXES = ("last modified", "feedback", "was this page helpful", "this is the multi-page printable view",
                 "return to the regular view", "click here to print", "items on this page refer to third party",
                 "create an issue", "edit this page")


def approx_tokens(text: str) -> int:
    """Rough token estimate (about 4 characters per token). Used only for chunking."""
    return max(1, len(text) // 4)


def fetch(urls: dict, raw_dir: Path, refresh: bool = False) -> dict:
    """Download each page once and keep it, so every run uses exactly the same text."""
    import requests
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, url in urls.items():
        existing = sorted(raw_dir.glob(f"{name}_*.html"))
        if existing and not refresh:
            files[name] = existing[-1]
            continue
        r = requests.get(url, timeout=60, headers={"User-Agent": "token-efficiency-research/1.0"})
        r.raise_for_status()
        path = raw_dir / f"{name}_{date.today().isoformat()}.html"
        path.write_text(r.text, encoding="utf-8")
        files[name] = path
    return files


def _clean(text: str) -> str:
    text = text.replace("¶", "").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def _block_text(el) -> str:
    if el.name == "pre":
        return "```\n" + el.get_text().strip("\n") + "\n```"
    if el.name == "table":
        rows = []
        for tr in el.find_all("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            rows.append(" | ".join(cells))
        return "\n".join(rows)
    text = _clean(el.get_text(" "))
    return ("- " + text) if el.name == "li" else text


def parse_sections(html: str, source: str) -> list:
    """Return sections: one per h2 heading of each page (content before the first h2 is 'Overview')."""
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup.select("nav, footer, aside, script, style, .td-page-meta, .feedback--title, .d-print-none"):
        bad.decompose()
    root = soup.select_one("main") or soup.body or soup
    sections, page, cur = [], None, None

    def start(sec_title):
        nonlocal cur
        cur = {"source": source, "page": page or source, "section": sec_title, "blocks": []}
        sections.append(cur)

    for el in root.find_all(HEAD_TAGS + BLOCK_TAGS):
        if el.name in BLOCK_TAGS and el.find_parent(BLOCK_TAGS):
            continue  # nested block: its text is already part of the parent block
        if el.name in HEAD_TAGS:
            title = _clean(el.get_text(" "))
            if not title:
                continue
            if el.name == "h1":
                page = re.sub(r"^\d+(\.\d+)*\s*-\s*", "", title)
                start("Overview")
            elif el.name == "h2":
                if cur is None:
                    start("Overview")
                start(title)
                cur["page"] = page or source
            else:
                if cur is None:
                    start("Overview")
                cur["blocks"].append({"sub": title, "text": ("### " if el.name == "h3" else "#### ") + title})
            continue
        text = _block_text(el)
        if not text or text.lower().startswith(SKIP_PREFIXES):
            continue
        if cur is None:
            start("Overview")
        cur["blocks"].append({"sub": None, "text": text})
    return [s for s in sections if any(b["sub"] is None for b in s["blocks"])]


def build_corpus(raw_files: dict, passage_tokens: int):
    """Turn raw HTML files into numbered sections (D...) and passages (P...)."""
    sections, passages = [], []
    for source, path in raw_files.items():
        html = Path(path).read_text(encoding="utf-8")
        sections.extend(parse_sections(html, source))
    out_sections = []
    for si, s in enumerate(sections, 1):
        sid = f"D{si:03d}"
        path_str = f"{s['page']} > {s['section']}"
        body = "\n".join(b["text"] for b in s["blocks"])
        out_sections.append({"id": sid, "source": s["source"], "page": s["page"], "section": s["section"],
                             "path": path_str, "text": body, "tokens": approx_tokens(body)})
        # pack blocks into passages of about `passage_tokens`
        buf, buf_sub, cur_sub = [], None, None

        def flush():
            nonlocal buf, buf_sub
            if buf and any(not t.startswith("#") for t in buf):
                p_path = path_str + (f" > {buf_sub}" if buf_sub else "")
                text = "\n".join(buf)
                passages.append({"id": f"P{len(passages) + 1:04d}", "section_id": sid, "page": s["page"],
                                 "section": s["section"], "path": p_path, "text": text,
                                 "tokens": approx_tokens(text)})
            buf, buf_sub = [], None

        for b in s["blocks"]:
            if b["sub"]:
                cur_sub = b["sub"]
                if buf and approx_tokens("\n".join(buf)) > passage_tokens * 0.5:
                    flush()
            pieces = [b["text"]]
            if approx_tokens(b["text"]) > passage_tokens:          # very long block: split by lines
                pieces, part = [], []
                for line in b["text"].split("\n"):
                    part.append(line)
                    if approx_tokens("\n".join(part)) >= passage_tokens:
                        pieces.append("\n".join(part)); part = []
                if part:
                    pieces.append("\n".join(part))
            for piece in pieces:
                if buf and approx_tokens("\n".join(buf + [piece])) > passage_tokens:
                    flush()
                if not buf:
                    buf_sub = cur_sub
                buf.append(piece)
        flush()
    return out_sections, passages


def save_jsonl(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
