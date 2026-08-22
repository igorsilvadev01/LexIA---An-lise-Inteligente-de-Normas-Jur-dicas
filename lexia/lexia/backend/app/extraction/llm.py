"""Extração via LLM com validação de schema e uma tentativa de reparo.

O acesso à rede fica atrás de um `Transport` injetável: em produção é HTTP
(Anthropic/OpenAI); nos testes é uma função que devolve strings. Assim a
lógica de parsing/validação/reparo é testada sem chave de API e sem rede.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Protocol

from pydantic import ValidationError

from ..models import LegalNorm
from .prompts import DEFAULT_VERSION, REPAIR_INSTRUCTION, build_prompt

Transport = Callable[[str, str], str]
"""``(system, user) -> texto da resposta do modelo``."""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class LLMError(RuntimeError):
    """Falha irrecuperável ao obter extração válida do modelo."""


class SupportsPost(Protocol):
    def post(self, url: str, *, headers: dict[str, str], json: dict) -> SupportsResponse: ...


class SupportsResponse(Protocol):
    status_code: int

    def json(self) -> dict: ...

    def raise_for_status(self) -> None: ...


def parse_json_payload(raw: str) -> dict:
    """Tolera cercas markdown e texto ao redor do JSON."""
    cleaned = _FENCE_RE.sub("", raw.strip())
    match = _JSON_BLOCK_RE.search(cleaned)
    if not match:
        raise LLMError("resposta do modelo não contém objeto JSON")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:  # pragma: no cover - mensagem depende do modelo
        raise LLMError(f"JSON inválido: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMError("JSON de topo não é um objeto")
    return payload


def http_transport(
    *,
    provider: str = "anthropic",
    model: str = "claude-3-5-sonnet-latest",
    timeout: float = 60.0,
    max_tokens: int = 4096,
) -> Transport:
    """Transport HTTP real (importa httpx sob demanda)."""

    def _send(system: str, user: str) -> str:
        import httpx

        if provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise LLMError("ANTHROPIC_API_KEY não definida")
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return "".join(block.get("text", "") for block in response.json().get("content", []))

        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise LLMError("OPENAI_API_KEY não definida")
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
                json={
                    "model": model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        raise LLMError(f"provedor não suportado: {provider}")

    return _send


class LLMExtractor:
    """Chama o modelo, valida contra :class:`LegalNorm` e tenta reparar uma vez."""

    def __init__(
        self,
        transport: Transport,
        *,
        prompt_version: str = DEFAULT_VERSION,
        model: str | None = None,
        max_document_chars: int = 24000,
    ) -> None:
        self.transport = transport
        self.prompt_version = prompt_version
        self.model = model
        self.max_document_chars = max_document_chars

    def extract(self, text: str) -> tuple[LegalNorm, list[str]]:
        warnings: list[str] = []
        document = text
        if len(document) > self.max_document_chars:
            document = document[: self.max_document_chars]
            warnings.append(
                f"documento truncado em {self.max_document_chars} caracteres antes do envio ao modelo"
            )

        system, user = build_prompt(document, self.prompt_version)
        raw = self.transport(system, user)
        try:
            return self._validate(raw), warnings
        except (LLMError, ValidationError) as first_error:
            warnings.append(f"primeira resposta inválida, tentando reparo: {first_error}")
            repair = f"{user}\n\n{REPAIR_INSTRUCTION.format(error=first_error)}"
            raw_retry = self.transport(system, repair)
            try:
                return self._validate(raw_retry), warnings
            except (LLMError, ValidationError) as second_error:
                raise LLMError(f"extração inválida após reparo: {second_error}") from second_error

    @staticmethod
    def _validate(raw: str) -> LegalNorm:
        return LegalNorm.model_validate(parse_json_payload(raw))
