"""Serviço de extração: escolhe o backend, mede latência e faz fallback."""

from __future__ import annotations

import time

from ..config import Settings, get_settings
from ..models import ExtractionResult
from . import rules
from .llm import LLMError, LLMExtractor, Transport, http_transport


class ExtractionService:
    """Fachada única usada pela API, pelo CLI e pela avaliação."""

    def __init__(self, settings: Settings | None = None, *, transport: Transport | None = None) -> None:
        self.settings = settings or get_settings()
        self._transport = transport

    @property
    def backend(self) -> str:
        if self.settings.extractor_backend == "llm" and (self._transport or self.settings.api_key):
            return "llm"
        return "rules"

    def _llm(self) -> LLMExtractor:
        transport = self._transport or http_transport(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            timeout=self.settings.llm_timeout,
        )
        return LLMExtractor(
            transport,
            prompt_version=self.settings.prompt_version,
            model=self.settings.llm_model,
        )

    def extract(self, *, document_id: str, text: str) -> ExtractionResult:
        started = time.perf_counter()
        backend = self.backend
        warnings: list[str] = []

        if backend == "llm":
            try:
                norm, warnings = self._llm().extract(text)
                return ExtractionResult(
                    document_id=document_id,
                    norm=norm,
                    backend="llm",
                    prompt_version=self.settings.prompt_version,
                    model=self.settings.llm_model,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    warnings=warnings,
                )
            except LLMError as exc:
                warnings.append(f"backend LLM falhou ({exc}); usando extrator de regras")

        norm, rule_warnings = rules.extract(text)
        return ExtractionResult(
            document_id=document_id,
            norm=norm,
            backend="rules",
            prompt_version=None,
            model=None,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=warnings + rule_warnings,
        )


def get_extractor(settings: Settings | None = None) -> ExtractionService:
    return ExtractionService(settings)
