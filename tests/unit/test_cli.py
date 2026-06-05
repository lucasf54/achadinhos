"""Aceite da CLI: o parser monta e os comandos roteiam sem precisar de banco."""
from __future__ import annotations

import pytest

from luachadinhos.cli import build_parser, main


def test_help_nao_quebra(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Lu Achadinhos" in out
    assert "db" in out and "collect" in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert "luachadinhos" in capsys.readouterr().out


def test_sem_comando_falha():
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([])
    assert exc.value.code != 0  # subcomando é obrigatório


def test_stubs_retornam_codigo_2(capsys):
    # Comandos ainda não implementados devem avisar e sair com 2, sem crashar.
    for cmd in (["publish"],):
        assert main(cmd) == 2
    assert "não implementado" in capsys.readouterr().out


def test_collect_dry_run_funciona(capsys):
    # collect --dry-run com categoria default roda sem erro
    rc = main(["collect", "--fonte", "ml", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "produtos ML" in out


def test_db_check_sem_banco_erro_amigavel(capsys):
    # Sem Postgres, deve retornar erro tratado (1), não traceback.
    rc = main(["db", "check"])
    assert rc == 1
    assert "Erro" in capsys.readouterr().err
