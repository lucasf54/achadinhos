"""Testes do repositório — sem banco (conn mockado)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from luachadinhos.db.repository import (
    _platform_id,
    upsert_product,
    criar_run,
    finalizar_run,
    inserir_offer,
    inserir_price_history,
    gravar_coleta,
)
from luachadinhos.models.produto import Produto


def _conn_mock(return_id=42):
    """Cria um conn mock cujo execute().fetchone() retorna (return_id,)."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (return_id,)
    return conn


def _produto(**kw) -> Produto:
    defaults = dict(
        plataforma="mercadolivre",
        source_id="MLB123",
        titulo="Fone Bluetooth",
        preco_atual=99.90,
        preco_original=149.90,
        desconto_pct=33,
        economia=50.0,
    )
    defaults.update(kw)
    return Produto(**defaults)


class TestPlatformId:
    def test_ml(self):
        assert _platform_id("mercadolivre") == 1

    def test_shopee(self):
        assert _platform_id("shopee") == 2

    def test_desconhecida(self):
        with pytest.raises(ValueError, match="desconhecida"):
            _platform_id("amazon")


class TestUpsertProduct:
    def test_retorna_id(self):
        conn = _conn_mock(return_id=7)
        pid = upsert_product(conn, _produto())
        assert pid == 7
        assert conn.execute.called

    def test_sql_contem_on_conflict(self):
        conn = _conn_mock()
        upsert_product(conn, _produto())
        sql = conn.execute.call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "RETURNING id" in sql


class TestCriarRun:
    def test_retorna_run_id(self):
        conn = _conn_mock(return_id=1)
        rid = criar_run(conn, "manha", platform_id=1)
        assert rid == 1

    def test_sem_platform(self):
        conn = _conn_mock(return_id=5)
        rid = criar_run(conn, "dev")
        assert rid == 5


class TestFinalizarRun:
    def test_chama_update(self):
        conn = MagicMock()
        finalizar_run(conn, run_id=1, n_collected=48, n_posted=5)
        assert conn.execute.called
        sql = conn.execute.call_args[0][0]
        assert "UPDATE collection_run" in sql


class TestInserirOffer:
    def test_retorna_offer_id(self):
        conn = _conn_mock(return_id=99)
        oid = inserir_offer(conn, product_id=7, run_id=1, produto=_produto())
        assert oid == 99

    def test_sql_upsert(self):
        conn = _conn_mock()
        inserir_offer(conn, product_id=7, run_id=1, produto=_produto())
        sql = conn.execute.call_args[0][0]
        assert "ON CONFLICT (product_id, run_id)" in sql


class TestInserirPriceHistory:
    def test_insere(self):
        conn = MagicMock()
        inserir_price_history(conn, product_id=7, preco=99.90)
        assert conn.execute.called
        sql = conn.execute.call_args[0][0]
        assert "price_history" in sql


class TestGravarColeta:
    def test_grava_lista(self):
        conn = _conn_mock(return_id=1)
        produtos = [_produto(), _produto(source_id="MLB456")]
        resultado = gravar_coleta(conn, run_id=1, produtos=produtos)
        assert len(resultado) == 2
        # 3 calls por produto: upsert + offer + price_history
        assert conn.execute.call_count == 6

    def test_erro_em_um_nao_quebra(self):
        conn = MagicMock()
        # Primeira chamada OK, segunda falha
        conn.execute.return_value.fetchone.side_effect = [
            (1,), (10,), None,  # produto 1 OK
            Exception("db error"),  # produto 2 falha no upsert
        ]
        produtos = [_produto(), _produto(source_id="MLB456")]
        resultado = gravar_coleta(conn, run_id=1, produtos=produtos)
        # Pelo menos 1 gravou
        assert len(resultado) >= 1

    def test_lista_vazia(self):
        conn = MagicMock()
        resultado = gravar_coleta(conn, run_id=1, produtos=[])
        assert resultado == []
        conn.execute.assert_not_called()
