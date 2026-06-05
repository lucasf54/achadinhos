"""Testes das consultas de histórico — sem banco (conn mockado)."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from luachadinhos.db.historico import (
    Stats30d,
    stats_preco_30d,
    stats_preco_30d_batch,
    ja_postado,
    ja_postado_batch,
    registrar_post,
)


def _conn_mock(fetchone_val=None, fetchall_val=None):
    conn = MagicMock()
    cursor = conn.execute.return_value
    cursor.fetchone.return_value = fetchone_val
    cursor.fetchall.return_value = fetchall_val or []
    return conn


class TestStats30d:
    def test_retorna_stats(self):
        conn = _conn_mock(fetchone_val=(150.0, 120.0, 8))
        stats = stats_preco_30d(conn, product_id=1)
        assert stats is not None
        assert stats.media == 150.0
        assert stats.minimo == 120.0
        assert stats.n_amostras == 8

    def test_sem_historico(self):
        conn = _conn_mock(fetchone_val=(None, None, 0))
        stats = stats_preco_30d(conn, product_id=1)
        assert stats is None

    def test_none_row(self):
        conn = _conn_mock(fetchone_val=None)
        stats = stats_preco_30d(conn, product_id=1)
        assert stats is None

    def test_janela_customizada(self):
        conn = _conn_mock(fetchone_val=(200.0, 180.0, 3))
        stats = stats_preco_30d(conn, product_id=1, janela_dias=7)
        assert stats.n_amostras == 3
        params = conn.execute.call_args[0][1]
        assert params["dias"] == 7


class TestStats30dBatch:
    def test_batch_retorna_dict(self):
        conn = _conn_mock(fetchall_val=[
            (1, 150.0, 120.0, 8),
            (2, 200.0, 190.0, 3),
        ])
        resultado = stats_preco_30d_batch(conn, [1, 2])
        assert len(resultado) == 2
        assert resultado[1].media == 150.0
        assert resultado[2].minimo == 190.0

    def test_batch_vazio(self):
        conn = MagicMock()
        resultado = stats_preco_30d_batch(conn, [])
        assert resultado == {}
        conn.execute.assert_not_called()


class TestJaPostado:
    def test_nunca_postado(self):
        conn = _conn_mock(fetchone_val=None)
        assert ja_postado(conn, 1, 1) is False

    def test_postado_recentemente(self):
        conn = MagicMock()
        # Primeiro execute: busca post
        # Segundo execute: calcula dias
        posted_at = datetime.now()
        results = [
            MagicMock(fetchone=MagicMock(return_value=(100.0, posted_at))),
            MagicMock(fetchone=MagicMock(return_value=(5,))),  # 5 dias atrás
        ]
        conn.execute.side_effect = results
        assert ja_postado(conn, 1, 1, repost_min_days=30) is True

    def test_postado_ha_muito_tempo(self):
        conn = MagicMock()
        posted_at = datetime.now() - timedelta(days=45)
        results = [
            MagicMock(fetchone=MagicMock(return_value=(100.0, posted_at))),
            MagicMock(fetchone=MagicMock(return_value=(45,))),  # 45 dias
        ]
        conn.execute.side_effect = results
        assert ja_postado(conn, 1, 1, repost_min_days=30) is False

    def test_preco_caiu_libera_repost(self):
        conn = MagicMock()
        posted_at = datetime.now() - timedelta(days=10)
        results = [
            MagicMock(fetchone=MagicMock(return_value=(100.0, posted_at))),
            MagicMock(fetchone=MagicMock(return_value=(10,))),
        ]
        conn.execute.side_effect = results
        # Preço caiu de 100 para 85 = 15% queda > 10% threshold
        assert ja_postado(conn, 1, 1, preco_atual=85.0) is False

    def test_preco_nao_caiu_suficiente(self):
        conn = MagicMock()
        posted_at = datetime.now() - timedelta(days=10)
        results = [
            MagicMock(fetchone=MagicMock(return_value=(100.0, posted_at))),
            MagicMock(fetchone=MagicMock(return_value=(10,))),
        ]
        conn.execute.side_effect = results
        # Preço caiu de 100 para 95 = 5% < 10%
        assert ja_postado(conn, 1, 1, preco_atual=95.0) is True


class TestJaPostadoBatch:
    def test_retorna_set(self):
        conn = _conn_mock(fetchall_val=[(1,), (3,)])
        bloqueados = ja_postado_batch(conn, [1, 2, 3], group_id=1)
        assert bloqueados == {1, 3}

    def test_vazio(self):
        conn = MagicMock()
        bloqueados = ja_postado_batch(conn, [], group_id=1)
        assert bloqueados == set()
        conn.execute.assert_not_called()


class TestRegistrarPost:
    def test_retorna_id(self):
        conn = _conn_mock(fetchone_val=(42,))
        pid = registrar_post(
            conn, product_id=1, offer_id=10, group_id=1,
            preco=99.90, desconto=33.0, mensagem="Oferta!"
        )
        assert pid == 42

    def test_mensagem_truncada(self):
        conn = _conn_mock(fetchone_val=(1,))
        msg_grande = "x" * 3000
        registrar_post(conn, 1, None, 1, 50.0, mensagem=msg_grande)
        params = conn.execute.call_args[0][1]
        assert len(params["msg"]) == 2000
