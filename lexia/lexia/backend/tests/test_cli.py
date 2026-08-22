from pathlib import Path

import pytest

from app.cli import main
from app.config import Settings


def test_ingest_cria_indice(settings: Settings, capsys: pytest.CaptureFixture):
    assert main(["ingest"]) == 0
    assert settings.index_path.exists()
    assert "chunks" in capsys.readouterr().out


def test_ingest_arquivo_unico(settings: Settings, capsys: pytest.CaptureFixture):
    caminho = settings.corpus_dir / "lei-4444-2021.txt"
    assert main(["ingest", "--path", str(caminho)]) == 0
    assert '"documents": 1' in capsys.readouterr().out


def test_search_imprime_resultados(settings: Settings, capsys: pytest.CaptureFixture):
    main(["ingest"])
    assert main(["search", "prazo para defesa escrita", "--top-k", "2"]) == 0
    saida = capsys.readouterr().out
    assert "Art. 3º" in saida and "#1" in saida


def test_extract_por_nome_de_arquivo(settings: Settings, capsys: pytest.CaptureFixture):
    main(["ingest"])
    assert main(["extract", "resolucao-118"]) == 0
    assert '"number": "118"' in capsys.readouterr().out


def test_extract_documento_inexistente(settings: Settings):
    main(["ingest"])
    assert main(["extract", "inexistente"]) == 1


def test_eval_escreve_relatorio(settings: Settings, tmp_path: Path):
    destino = tmp_path / "out" / "EVALUATION.md"
    assert main(["eval", "--out", str(destino)]) == 0
    conteudo = destino.read_text(encoding="utf-8")
    assert "Macro-F1" in conteudo and "Recuperação" in conteudo


def test_eval_falha_quando_abaixo_do_limiar(settings: Settings):
    assert main(["eval", "--min-macro-f1", "0.99"]) == 2
    assert main(["eval", "--min-macro-f1", "0.90"]) == 0
