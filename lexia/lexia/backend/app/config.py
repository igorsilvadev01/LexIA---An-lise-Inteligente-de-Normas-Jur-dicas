"""Configuração da aplicação, lida de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    """Parâmetros de execução.

    O sistema roda 100% offline por padrão (`extractor_backend="rules"`).
    Definindo `LEXIA_EXTRACTOR=llm` + a chave do provedor, a mesma interface
    passa a usar um LLM, sem mudar nada no resto do pipeline.
    """

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("LEXIA_DATA_DIR", str(BASE_DIR / "data"))))
    corpus_dir: Path = field(init=False)
    eval_dir: Path = field(init=False)
    index_path: Path = field(init=False)

    extractor_backend: str = field(default_factory=lambda: os.getenv("LEXIA_EXTRACTOR", "rules").lower())
    llm_provider: str = field(default_factory=lambda: os.getenv("LEXIA_LLM_PROVIDER", "anthropic").lower())
    llm_model: str = field(default_factory=lambda: os.getenv("LEXIA_LLM_MODEL", "claude-3-5-sonnet-latest"))
    llm_timeout: float = field(default_factory=lambda: _env_float("LEXIA_LLM_TIMEOUT", 60.0))
    prompt_version: str = field(default_factory=lambda: os.getenv("LEXIA_PROMPT_VERSION", "v2"))

    chunk_max_chars: int = field(default_factory=lambda: _env_int("LEXIA_CHUNK_MAX_CHARS", 1200))
    chunk_overlap: int = field(default_factory=lambda: _env_int("LEXIA_CHUNK_OVERLAP", 120))
    top_k: int = field(default_factory=lambda: _env_int("LEXIA_TOP_K", 5))
    persist: bool = field(default_factory=lambda: _env_bool("LEXIA_PERSIST", True))

    def __post_init__(self) -> None:
        self.corpus_dir = self.data_dir / "corpus"
        self.eval_dir = self.data_dir / "eval"
        self.index_path = self.data_dir / "index" / "store.json"

    @property
    def api_key(self) -> str | None:
        env_name = "ANTHROPIC_API_KEY" if self.llm_provider == "anthropic" else "OPENAI_API_KEY"
        return os.getenv(env_name)

    def ensure_dirs(self) -> None:
        for path in (self.corpus_dir, self.eval_dir, self.index_path.parent):
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
