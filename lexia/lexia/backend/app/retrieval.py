"""Fusão de rankings (Reciprocal Rank Fusion) para busca híbrida."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FusedHit:
    id: str
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0


def reciprocal_rank_fusion(
    rankings: dict[str, list[tuple[str, float]]],
    *,
    k: int = 60,
    weights: dict[str, float] | None = None,
) -> list[FusedHit]:
    """Combina listas ranqueadas heterogêneas sem precisar calibrar escalas.

    RRF soma ``w / (k + rank)`` por lista, o que é robusto ao fato de BM25 e
    cosseno viverem em faixas numéricas diferentes (BM25 é ilimitado, cosseno
    está em [0, 1]) — normalizar min-max seria instável com poucos resultados.
    """
    weights = weights or {}
    fused: dict[str, FusedHit] = {}
    for source, ranked in rankings.items():
        weight = weights.get(source, 1.0)
        for rank, (doc_id, raw_score) in enumerate(ranked, start=1):
            hit = fused.setdefault(doc_id, FusedHit(id=doc_id, score=0.0))
            hit.score += weight / (k + rank)
            if source == "lexical":
                hit.lexical_score = raw_score
            elif source == "semantic":
                hit.semantic_score = raw_score
    return sorted(fused.values(), key=lambda hit: (-hit.score, hit.id))
