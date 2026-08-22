"""Harness de avaliação: métricas por campo do schema e métricas de recuperação."""

from .metrics import ConfusionAccumulator, prf, token_set_similarity
from .runner import evaluate_extraction, evaluate_retrieval, render_markdown

__all__ = [
    "ConfusionAccumulator",
    "prf",
    "token_set_similarity",
    "evaluate_extraction",
    "evaluate_retrieval",
    "render_markdown",
]
