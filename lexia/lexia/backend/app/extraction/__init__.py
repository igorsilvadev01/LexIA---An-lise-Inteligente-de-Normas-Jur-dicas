"""Extração estruturada: baseline determinístico (regras) + backend LLM."""

from .service import ExtractionService, get_extractor

__all__ = ["ExtractionService", "get_extractor"]
