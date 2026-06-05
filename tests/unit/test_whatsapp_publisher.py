"""Testes do publisher WhatsApp — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.publishers.whatsapp import WhatsAppPublisher
from luachadinhos.models.produto import Produto


def _p(titulo="Fone", msg="mensagem teste") -> Produto:
    p = Produto(plataforma="ml", source_id="1", titulo=titulo)
    p.mensagem_wa = msg
    return p


class TestWhatsAppPublisher:
    @patch("luachadinhos.publishers.whatsapp.requests.get")
    def test_health_check_ok(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "connected"}
        wa = WhatsAppPublisher()
        assert wa.health_check() is True

    @patch("luachadinhos.publishers.whatsapp.requests.get")
    def test_health_check_nao_conectado(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "disconnected"}
        wa = WhatsAppPublisher()
        assert wa.health_check() is False

    @patch("luachadinhos.publishers.whatsapp.requests.get")
    def test_health_check_erro(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        wa = WhatsAppPublisher()
        assert wa.health_check() is False

    @patch("luachadinhos.publishers.whatsapp.requests.post")
    def test_enviar_ok(self, mock_post):
        mock_post.return_value.json.return_value = {"success": True}
        wa = WhatsAppPublisher()
        assert wa.enviar_mensagem("grupo1", "oi") is True

    @patch("luachadinhos.publishers.whatsapp.requests.post")
    def test_enviar_falha(self, mock_post):
        mock_post.return_value.json.return_value = {"success": False, "error": "banned"}
        wa = WhatsAppPublisher()
        assert wa.enviar_mensagem("grupo1", "oi") is False

    @patch("luachadinhos.publishers.whatsapp.time.sleep")
    @patch("luachadinhos.publishers.whatsapp.requests.post")
    def test_publicar(self, mock_post, mock_sleep):
        mock_post.return_value.json.return_value = {"success": True}
        wa = WhatsAppPublisher()
        produtos = [_p("Fone A"), _p("Fone B")]
        resultados = wa.publicar(produtos, ["grupo1"])
        assert len(resultados) == 2
        assert all(ok for _, _, ok in resultados)

    @patch("luachadinhos.publishers.whatsapp.time.sleep")
    @patch("luachadinhos.publishers.whatsapp.requests.post")
    def test_publicar_sem_mensagem(self, mock_post, mock_sleep):
        wa = WhatsAppPublisher()
        p = _p(msg="")
        resultados = wa.publicar([p], ["grupo1"])
        assert resultados[0][2] is False  # sem mensagem = falha
