"""Métricas de qualidade da extração.

Decisões de medição (explícitas de propósito — métrica mal definida engana mais
que a ausência de métrica):

* **Campos escalares** (tipo, número, datas...) são comparados por igualdade
  após normalização (minúsculas, sem acento). Prever um valor onde o golden diz
  ``null`` conta como falso positivo — abster-se é melhor que inventar.
* **Campo ``subject``** (ementa) é texto livre; usamos similaridade de
  Jaccard de tokens com limiar alto (0.8), porque pequenas variações de
  pontuação não deveriam ser punidas.
* **Listas** (obrigações, prazos, penalidades, referências) usam pareamento
  guloso 1-para-1 por similaridade, com limiares por tipo de item. Sem
  pareamento, a ordem da lista influenciaria o resultado — o que não faz
  sentido para conjuntos de fatos.
* Reportamos **macro-F1** (média por campo, dá peso igual a campos raros) e
  **micro-F1** (agregado por item, dominado por campos com mais itens).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from ..models import Deadline, FieldScore, LegalNorm, Obligation, Penalty
from ..text import normalize_key, tokenize

SCALAR_FIELDS = (
    "norm_type",
    "number",
    "year",
    "issuing_body",
    "publication_date",
    "effective_date",
    "subject",
)
LIST_FIELDS = ("obligations", "deadlines", "penalties", "references")

OBLIGATION_THRESHOLD = 0.4
SUBJECT_THRESHOLD = 0.8


def token_set_similarity(left: str, right: str) -> float:
    """Jaccard entre conjuntos de tokens normalizados (0.0 a 1.0)."""
    a, b = set(tokenize(left)), set(tokenize(right))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def prf(tp: int, n_pred: int, n_gold: int) -> tuple[float, float, float]:
    """Precisão, revocação e F1 a partir da contagem de acertos."""
    precision = tp / n_pred if n_pred else (1.0 if n_gold == 0 else 0.0)
    recall = tp / n_gold if n_gold else (1.0 if n_pred == 0 else 0.0)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def greedy_match(
    predicted: Sequence,
    gold: Sequence,
    similarity: Callable[[object, object], float],
    threshold: float,
) -> int:
    """Pareamento guloso 1-para-1: devolve o número de acertos (TP)."""
    used: set[int] = set()
    matched = 0
    for pred in predicted:
        best_index, best_score = -1, 0.0
        for index, gold_item in enumerate(gold):
            if index in used:
                continue
            score = similarity(pred, gold_item)
            if score > best_score:
                best_index, best_score = index, score
        if best_index >= 0 and best_score >= threshold:
            used.add(best_index)
            matched += 1
    return matched


def _same_article(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return True  # não penaliza ausência de metadado
    return normalize_key(left) == normalize_key(right)


def obligation_similarity(pred: Obligation, gold: Obligation) -> float:
    if not _same_article(pred.article, gold.article):
        return 0.0
    action = token_set_similarity(pred.action, gold.action)
    actor = token_set_similarity(pred.actor or "", gold.actor or "")
    return 0.8 * action + 0.2 * actor


def deadline_similarity(pred: Deadline, gold: Deadline) -> float:
    if not _same_article(pred.article, gold.article):
        return 0.0
    return 1.0 if (pred.value == gold.value and pred.unit == gold.unit) else 0.0


def penalty_similarity(pred: Penalty, gold: Penalty) -> float:
    if not _same_article(pred.article, gold.article):
        return 0.0
    return 1.0 if pred.kind == gold.kind else 0.0


def reference_similarity(pred: str, gold: str) -> float:
    return 1.0 if normalize_key(pred) == normalize_key(gold) else 0.0


LIST_MATCHERS: dict[str, tuple[Callable, float]] = {
    "obligations": (obligation_similarity, OBLIGATION_THRESHOLD),
    "deadlines": (deadline_similarity, 1.0),
    "penalties": (penalty_similarity, 1.0),
    "references": (reference_similarity, 1.0),
}


def scalar_match(field_name: str, predicted, gold) -> tuple[int, int, int]:
    """Devolve ``(tp, n_pred, n_gold)`` para um campo escalar."""
    n_pred = 0 if predicted in (None, "", "desconhecido") else 1
    n_gold = 0 if gold in (None, "", "desconhecido") else 1
    if not n_pred or not n_gold:
        return 0, n_pred, n_gold
    if field_name == "subject":
        tp = int(token_set_similarity(str(predicted), str(gold)) >= SUBJECT_THRESHOLD)
    else:
        tp = int(normalize_key(str(predicted)) == normalize_key(str(gold)))
    return tp, n_pred, n_gold


@dataclass
class ConfusionAccumulator:
    """Acumula TP/predições/gold por campo ao longo de vários documentos."""

    tp: dict[str, int] = field(default_factory=dict)
    n_pred: dict[str, int] = field(default_factory=dict)
    n_gold: dict[str, int] = field(default_factory=dict)

    def add(self, field_name: str, tp: int, n_pred: int, n_gold: int) -> None:
        self.tp[field_name] = self.tp.get(field_name, 0) + tp
        self.n_pred[field_name] = self.n_pred.get(field_name, 0) + n_pred
        self.n_gold[field_name] = self.n_gold.get(field_name, 0) + n_gold

    def add_norm(self, predicted: LegalNorm, gold: LegalNorm) -> None:
        for name in SCALAR_FIELDS:
            self.add(name, *scalar_match(name, getattr(predicted, name), getattr(gold, name)))
        for name in LIST_FIELDS:
            similarity, threshold = LIST_MATCHERS[name]
            pred_items = getattr(predicted, name)
            gold_items = getattr(gold, name)
            tp = greedy_match(pred_items, gold_items, similarity, threshold)
            self.add(name, tp, len(pred_items), len(gold_items))

    def field_scores(self) -> list[FieldScore]:
        scores: list[FieldScore] = []
        for name in list(SCALAR_FIELDS) + list(LIST_FIELDS):
            precision, recall, f1 = prf(
                self.tp.get(name, 0), self.n_pred.get(name, 0), self.n_gold.get(name, 0)
            )
            scores.append(
                FieldScore(
                    field=name,
                    precision=round(precision, 4),
                    recall=round(recall, 4),
                    f1=round(f1, 4),
                    support=self.n_gold.get(name, 0),
                    predicted=self.n_pred.get(name, 0),
                )
            )
        return scores

    def macro_f1(self) -> float:
        scores = self.field_scores()
        return round(sum(s.f1 for s in scores) / len(scores), 4) if scores else 0.0

    def micro_f1(self) -> float:
        tp = sum(self.tp.values())
        _, _, f1 = prf(tp, sum(self.n_pred.values()), sum(self.n_gold.values()))
        return round(f1, 4)


def recall_at_k(retrieved: Iterable[str], relevant: set[str], k: int) -> float:
    """Fração dos itens relevantes encontrados nos ``k`` primeiros resultados."""
    if not relevant:
        return 0.0
    top = list(retrieved)[:k]
    return len([item for item in set(top) if item in relevant]) / len(relevant)


def mean_reciprocal_rank(retrieved: Iterable[str], relevant: set[str]) -> float:
    """1/posição do primeiro resultado relevante (0.0 se nenhum)."""
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0
