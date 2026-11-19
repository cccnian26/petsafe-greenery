"""
Naive keyword retrieval (BM25) -- the retrieval half of Baseline 2.

This is deliberately a *plain* retrieval setup: bag-of-words BM25 over the
catalogue text, with **no negative toxicological filtering**.  That is the
whole point of the baseline: it shows what happens when you retrieve on
relevance alone and then let the LLM decide what to recommend.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .db import PlantDatabase, PlantRecord, get_database

_TOKEN = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "the", "is", "are", "and", "or", "but", "for", "with", "my",
    "in", "on", "of", "to", "it", "this", "that", "there", "has", "have",
    "i", "we", "you", "they", "live", "lives", "household", "space", "shares",
    "balcony", "courtyard", "design", "planting", "scheme", "plant", "plants",
    "mentioned", "brief", "client", "wants", "please", "help", "want", "need",
    "sunlight", "sun", "light", "moisture", "water", "soil", "pet", "pets",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(str(text).lower()) if t not in STOPWORDS]


class BM25Retriever:
    """Standard Okapi BM25 over the plant catalogue."""

    def __init__(self, db: PlantDatabase | None = None, k1: float = 1.5, b: float = 0.75):
        self.db = db or get_database()
        self.k1 = k1
        self.b = b
        self.docs: list[list[str]] = []
        self.records: list[PlantRecord] = self.db.records
        for rec in self.records:
            text = " ".join([
                rec.scientific_name, rec.common_name, rec.plant_type,
                rec.light.replace("_", " "), rec.moisture, rec.notes,
            ])
            self.docs.append(tokenize(text))
        self.N = len(self.docs)
        self.avgdl = (sum(len(d) for d in self.docs) / self.N) if self.N else 0.0
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        self.idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()
        }

    def search(self, query: str, top_k: int = 8) -> list[tuple[PlantRecord, float]]:
        q = tokenize(query)
        scores: list[float] = []
        for d in self.docs:
            tf = Counter(d)
            dl = len(d)
            score = 0.0
            for term in q:
                if term not in tf:
                    continue
                idf = self.idf.get(term, 0.0)
                f = tf[term]
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                score += idf * (f * (self.k1 + 1)) / (denom or 1)
            scores.append(score)
        ranked = sorted(zip(self.records, scores), key=lambda x: -x[1])[:top_k]
        return [(rec, round(score, 4)) for rec, score in ranked]

    def context(self, query: str, top_k: int = 8) -> list[dict]:
        """Return retrieval context WITHOUT any toxicity information."""
        out = []
        for rec, score in self.search(query, top_k=top_k):
            d = rec.public_dict()
            d["retrieval_score"] = score
            # the naive baseline never sees the safety labels
            d.pop("toxic_to_cats", None)
            d.pop("toxic_to_dogs", None)
            d.pop("source_url", None)
            out.append(d)
        return out
