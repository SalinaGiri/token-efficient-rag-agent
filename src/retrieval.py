"""Retrieval: naive top-k sections (baseline) and adaptive, precision-first passages (technique T1)."""
import hashlib
import time
from pathlib import Path

import numpy as np


class Embedder:
    """Bi-encoder: turns texts into vectors so similar texts can be found quickly."""
    def __init__(self, name: str):
        from sentence_transformers import SentenceTransformer
        self.name = name
        self.model = SentenceTransformer(name)

    def encode(self, texts):
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False))


class Reranker:
    """Cross-encoder: reads the question and a passage together and scores relevance (higher = more relevant)."""
    def __init__(self, name: str):
        from sentence_transformers import CrossEncoder
        self.name = name
        self.model = CrossEncoder(name)

    def score(self, query: str, texts):
        if not texts:
            return np.zeros(0)
        return np.asarray(self.model.predict([(query, t) for t in texts], show_progress_bar=False), dtype=float)


def passage_view(p: dict) -> str:
    return f"{p['path']}\n{p['text']}"


class Retriever:
    def __init__(self, sections, passages, embedder, reranker, cache_dir: Path = None):
        self.sections = {s["id"]: s for s in sections}
        self.passages = passages
        self.by_id = {p["id"]: p for p in passages}
        self.embedder, self.reranker = embedder, reranker
        texts = [passage_view(p) for p in passages]
        key = hashlib.sha1(("|".join(texts) + getattr(embedder, "name", "")).encode()).hexdigest()[:12]
        cache = Path(cache_dir) / f"emb_{key}.npy" if cache_dir else None
        if cache and cache.exists():
            self.emb = np.load(cache)
        else:
            self.emb = embedder.encode(texts)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                np.save(cache, self.emb)

    def _ranked(self, query: str):
        q = self.embedder.encode([query])[0]
        sims = self.emb @ q
        return np.argsort(-sims), sims

    def baseline_sections(self, query: str, k: int):
        """Naive RAG: find the most similar passages, return their whole parent sections (top-k unique)."""
        t0 = time.perf_counter()
        order, _ = self._ranked(query)
        out = []
        for i in order:
            sid = self.passages[i]["section_id"]
            if sid not in out:
                out.append(sid)
            if len(out) == k:
                break
        items = [{"id": sid, "path": self.sections[sid]["path"], "text": self.sections[sid]["text"]} for sid in out]
        return items, (time.perf_counter() - t0) * 1000, {}

    def adaptive_passages(self, query: str, tau: float, candidates: int, kmax: int):
        """T1: retrieve candidates, rerank, keep only passages scoring >= tau (at most kmax; possibly none)."""
        t0 = time.perf_counter()
        order, _ = self._ranked(query)
        cand = [self.passages[i] for i in order[:candidates]]
        scores = self.reranker.score(query, [passage_view(p) for p in cand])
        ranked = sorted(zip(cand, scores), key=lambda x: -x[1])
        kept = [(p, float(s)) for p, s in ranked if s >= tau][:kmax]
        items = [{"id": p["id"], "path": p["path"], "text": p["text"]} for p, _ in kept]
        info = {"scores": {p["id"]: round(s, 3) for p, s in kept},
                "top_score": round(float(ranked[0][1]), 3) if ranked else None}
        return items, (time.perf_counter() - t0) * 1000, info

    def top_rerank_score(self, query: str, candidates: int) -> float:
        order, _ = self._ranked(query)
        cand = [self.passages[i] for i in order[:candidates]]
        return float(np.max(self.reranker.score(query, [passage_view(p) for p in cand])))

    def items_for(self, passage_ids):
        return [{"id": pid, "path": self.by_id[pid]["path"], "text": self.by_id[pid]["text"]}
                for pid in passage_ids if pid in self.by_id]
