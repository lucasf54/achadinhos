"""Testes do publisher Telegram — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.publishers.telegram import TelegramPublisher
from luachadinhos.models.produto import Produto


def _p(titulo="Fone Bluetooth", msg="mensagem teste", imagem="") -> Produto:
    p = Produto(plataforma="ml", source_id="MLB1", titulo=titulo, imagem=imagem)
    p.mensagem_wa = msg
    return p


class TestTelegramPublisher:
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_texto_ok(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        assert tg.enviar_texto("chat1", "oi") is True

    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_texto_falha(self, mock_post):
        mock_post.return_value.json.return_value = {
            "ok": False, "description": "chat not found"
        }
        mock_post.return_value.status_code = 400
        tg = TelegramPublisher("token123")
        assert tg.enviar_texto("chat_invalido", "oi") is False

    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_texto_excecao(self, mock_post):
        mock_post.side_effect = Exception("timeout")
        tg = TelegramPublisher("token123")
        assert tg.enviar_texto("chat1", "oi") is False

    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_com_imagem_ok(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        assert tg.enviar_com_imagem("chat1", "https://img.jpg", "caption") is True

    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_com_imagem_fallback_texto(self, mock_post):
        # Primeiro call (foto) falha, segundo (texto) OK
        mock_post.return_value.json.side_effect = [
            {"ok": False, "description": "wrong url"},
            {"ok": True},
        ]
        mock_post.return_value.status_code = 400
        tg = TelegramPublisher("token123")
        assert tg.enviar_com_imagem("chat1", "bad_url", "caption") is True

    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_enviar_sem_imagem_usa_texto(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        assert tg.enviar_com_imagem("chat1", "", "caption") is True

    @patch("luachadinhos.publishers.telegram.time.sleep")
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_publicar(self, mock_post, mock_sleep):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        produtos = [_p("Fone A"), _p("Fone B")]
        resultados = tg.publicar(produtos, ["chat1"])
        assert len(resultados) == 2
        assert all(ok for _, _, ok in resultados)

    @patch("luachadinhos.publishers.telegram.time.sleep")
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_publicar_com_imagem(self, mock_post, mock_sleep):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        p = _p(imagem="https://http2.mlstatic.com/D_test.jpg")
        resultados = tg.publicar([p], ["chat1"], com_imagem=True)
        assert resultados[0][2] is True
        # Verifica que chamou sendPhoto (não sendMessage)
        url_chamada = mock_post.call_args[1]["json"].get("photo") or mock_post.call_args[0][0]
        # Pelo menos uma chamada deve ter "photo" no payload
        calls = mock_post.call_args_list
        payloads = [c[1].get("json", {}) for c in calls]
        assert any("photo" in p for p in payloads)

    @patch("luachadinhos.publishers.telegram.time.sleep")
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_publicar_sem_mensagem(self, mock_post, mock_sleep):
        tg = TelegramPublisher("token123")
        p = _p(msg="")
        resultados = tg.publicar([p], ["chat1"])
        assert resultados[0][2] is False

    @patch("luachadinhos.publishers.telegram.time.sleep")
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_publicar_multiplos_chats(self, mock_post, mock_sleep):
        mock_post.return_value.json.return_value = {"ok": True}
        tg = TelegramPublisher("token123")
        resultados = tg.publicar([_p()], ["chat1", "chat2"])
        assert len(resultados) == 2
        assert resultados[0][1] == "chat1"
        assert resultados[1][1] == "chat2"

    @patch("luachadinhos.publishers.telegram.time.sleep")
    @patch("luachadinhos.publishers.telegram.requests.post")
    def test_rate_limit_retry(self, mock_post, mock_sleep):
        # Primeiro: rate-limit, segundo: OK
        mock_post.return_value.json.side_effect = [
            {"ok": False, "description": "Too Many Requests",
             "parameters": {"retry_after": 5}},
            {"ok": True},
        ]
        mock_post.return_value.status_code = 429
        tg = TelegramPublisher("token123")
        assert tg.enviar_texto("chat1", "msg") is True
        mock_sleep.assert_called_with(5)
