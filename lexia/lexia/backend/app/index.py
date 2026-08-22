"""Índices de recuperação implementados do zero (NumPy), sem serviço externo.

Duas visões complementares do mesmo corpus:

* :class:`Bm25Index` — ranking lexical Okapi BM25 (bom para número de artigo,
  termos raros, citações literais como "Lei nº 13.709").
* :class:`TfidfIndex` — vetores TF-IDF normalizados + similaridade de cosseno,
  o "vector store" local. A interface (`add`/`search`) é a mesma que um
  Chroma/FAISS exporia, então trocar por embeddings de verdade é substituir
  a classe, não o pipeline.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .text import tokenize


@dataclass
class Bm25Index:
    """Okapi BM25 (k1, b) sobre tokens já normalizados."""

    k1: float = 1.5
    b: float = 0.75
    ids: list[str] = field(default_factory=list)
    _docs: list[Counter] = field(default_factory=list)
    _lengths: list[int] = field(default_factory=list)
    _df: Counter = field(default_factory=Counter)

    @property
    def size(self) -> int:
        return len(self.ids)

    def add(self, doc_id: str, text: str) -> None:
        tokens = tokenize(text)
        counts = Counter(tokens)
        self.ids.append(doc_id)
        self._docs.append(counts)
        self._lengths.append(max(1, len(tokens)))
        for term in counts:
            self._df[term] += 1

    def _idf(self, term: str) -> float:
        n = self.size
        df = self._df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(
        self, query: str, top_k: int = 5, *, allowed_ids: set[str] | None = None
    ) -> list[tuple[str, float]]:
        if self.size == 0:
            return []
        q_terms = tokenize(query)
        if not q_terms:
            return []
        avgdl = sum(self._lengths) / self.size
        scores: list[tuple[str, float]] = []
        for idx, counts in enumerate(self._docs):
            if allowed_ids is not None and self.ids[idx] not in allowed_ids:
                continue
            length = self._lengths[idx]
            score = 0.0
            for term in q_terms:
                tf = counts.get(term, 0)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * length / avgdl)
                score += self._idf(term) * (tf * (self.k1 + 1)) / denom
            if score > 0:
                scores.append((self.ids[idx], score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return scores[:top_k]


class TfidfIndex:
    """Vector store local: TF-IDF (tf sublinear) + cosseno."""

    def __init__(self) -> None:
        self.ids: list[str] = []
        self._token_lists: list[list[str]] = []
        self._vocab: dict[str, int] = {}
        self._matrix: np.ndarray | None = None
        self._idf: np.ndarray | None = None

    @property
    def size(self) -> int:
        return len(self.ids)

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    def add(self, doc_id: str, text: str) -> None:
        self.ids.append(doc_id)
        self._token_lists.append(tokenize(text))
        self._matrix = None  # invalida; reconstruído no próximo build/search

    def build(self) -> None:
        """(Re)constrói a matriz esparsa densificada e os pesos IDF."""
        if self.size == 0:
            self._matrix = np.zeros((0, 0), dtype=np.float32)
            self._idf = np.zeros((0,), dtype=np.float32)
            self._vocab = {}
            return

        vocab: dict[str, int] = {}
        for tokens in self._token_lists:
            for token in tokens:
                if token not in vocab:
                    vocab[token] = len(vocab)
        self._vocab = vocab

        n_docs, n_terms = self.size, len(vocab)
        tf = np.zeros((n_docs, n_terms), dtype=np.float32)
        for row, tokens in enumerate(self._token_lists):
            for token, count in Counter(tokens).items():
                tf[row, vocab[token]] = 1.0 + math.log(count)

        df = (tf > 0).sum(axis=0)
        self._idf = (np.log((n_docs + 1) / (df + 1)) + 1.0).astype(np.float32)
        matrix = tf * self._idf
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._matrix = (matrix / norms).astype(np.float32)

    def _vectorize(self, text: str) -> np.ndarray | None:
        assert self._idf is not None
        tokens = [t for t in tokenize(text) if t in self._vocab]
        if not tokens:
            return None
        vector = np.zeros((len(self._vocab),), dtype=np.float32)
        for token, count in Counter(tokens).items():
            vector[self._vocab[token]] = 1.0 + math.log(count)
        vector *= self._idf
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return None
        return vector / norm

    def search(
        self, query: str, top_k: int = 5, *, allowed_ids: set[str] | None = None
    ) -> list[tuple[str, float]]:
        if self._matrix is None:
            self.build()
        if self.size == 0 or self._matrix is None or self._matrix.size == 0:
            return []
        vector = self._vectorize(query)
        if vector is None:
            return []
        scores = self._matrix @ vector
        order = np.argsort(-scores)
        selected: list[tuple[str, float]] = []
        for i in order:
            if scores[i] <= 0:
                break
            if allowed_ids is not None and self.ids[i] not in allowed_ids:
                continue
            selected.append((self.ids[i], float(scores[i])))
            if len(selected) >= max(top_k, 1):
                break
        return selected
