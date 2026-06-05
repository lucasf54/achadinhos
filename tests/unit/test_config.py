"""Config central: carregar_filtros() funciona sem banco e respeita overrides."""
from __future__ import annotations

from luachadinhos.config.runtime_config import carregar_filtros, _filtros_do_env
from luachadinhos.models.filtros import Filtros


def test_filtros_do_env_tem_defaults_sensatos():
    f = _filtros_do_env()
    assert isinstance(f, Filtros)
    assert f.desconto_min >= 0
    assert 0 <= f.avaliacao_min <= 5
    assert f.top_por_disparo >= 1


def test_carregar_filtros_sem_banco_nao_quebra():
    # Em dev/teste não há Postgres; deve cair nos defaults sem lançar exceção.
    f = carregar_filtros()
    assert isinstance(f, Filtros)
    assert f.top_por_disparo >= 1


def test_overrides_vencem():
    f = carregar_filtros(overrides={"top_por_disparo": 99, "desconto_min": 35})
    assert f.top_por_disparo == 99
    assert f.desconto_min == 35


def test_overrides_invalidos_sao_ignorados():
    # Chave inexistente não deve quebrar nem ser aplicada.
    f = carregar_filtros(overrides={"campo_que_nao_existe": 123})
    assert not hasattr(f, "campo_que_nao_existe")


def test_filtros_imutavel_com_copia():
    f = carregar_filtros()
    f2 = f.com(top_por_disparo=7)
    assert f2.top_por_disparo == 7
    assert f is not f2  # cópia, não mutação
