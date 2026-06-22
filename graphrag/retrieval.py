"""Lightweight TF-IDF retrieval over document chunks.

This is a compact, dependency-free implementation of TF-IDF with cosine
similarity. The chunk corpus is small (tens of rows), so a pure-Python index is
both fast enough and keeps heavy scientific dependencies (scikit-learn, scipy,
numpy) out of the serverless bundle.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache

from .dataset import Row, get_table

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A small English stop-word list, mirroring the original scikit-learn config.
_STOP_WORDS = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    to was were will with this these those not no than then over under between""".split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP_WORDS and len(t) > 1]


class TfidfIndex:
    """A TF-IDF index over a list of chunk rows, with cosine-similarity search."""

    def __init__(self, chunks: list[Row]):
        self.chunks = chunks
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._build()

    @staticmethod
    def _document_text(chunk: Row) -> str:
        """Searchable text for a chunk: body plus summary and section metadata."""
        return " ".join(
            str(chunk.get(field, "") or "")
            for field in ("chunk_text", "chunk_summary", "section_name")
        )

    def _build(self) -> None:
        n_docs = len(self.chunks)
        if n_docs == 0:
            return

        doc_tokens = [_tokenize(self._document_text(c)) for c in self.chunks]

        document_frequency: Counter = Counter()
        for tokens in doc_tokens:
            for term in set(tokens):
                document_frequency[term] += 1

        # Smoothed IDF, matching scikit-learn's default formulation.
        self._idf = {
            term: math.log((1 + n_docs) / (1 + df)) + 1.0
            for term, df in document_frequency.items()
        }

        for tokens in doc_tokens:
            self._vectors.append(self._vectorize(tokens))

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        vector = {term: count * self._idf.get(term, 0.0) for term, count in counts.items()}
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        if norm == 0:
            return {}
        return {term: weight / norm for term, weight in vector.items()}

    def search(
        self, question: str, patient_id: str = "all", top_k: int = 8
    ) -> list[Row]:
        """Return the ``top_k`` most relevant chunks, optionally scoped to a patient."""
        if not self._vectors:
            return []

        query_vector = self._vectorize(_tokenize(question))
        if not query_vector:
            return []

        candidates = range(len(self.chunks))
        if patient_id != "all":
            candidates = [
                i
                for i in candidates
                if str(self.chunks[i].get("patient_id", "")) == str(patient_id)
            ]

        scored: list[tuple[float, int]] = []
        for i in candidates:
            doc_vector = self._vectors[i]
            if not doc_vector:
                continue
            # Cosine similarity reduces to a dot product of unit vectors.
            shared = query_vector.keys() & doc_vector.keys()
            score = sum(query_vector[t] * doc_vector[t] for t in shared)
            if score > 0:
                scored.append((score, i))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        results: list[Row] = []
        for score, i in scored[:top_k]:
            chunk = dict(self.chunks[i])
            chunk["similarity_score"] = round(score, 4)
            results.append(chunk)
        return results


@lru_cache(maxsize=1)
def get_index() -> TfidfIndex:
    """Return the TF-IDF index over the dataset's document chunks (built once)."""
    return TfidfIndex(get_table("document_chunks"))
