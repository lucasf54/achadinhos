"""Testes do notificador Telegram — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.control.notifier import TelegramNotifier


class TestTelegramNotifier:
    def test_nao_configurado(self):
        n = TelegramNotifier("", "")
        assert n.configurado is False
        assert n.enviar("teste") is False

    def test_configurado(self):
        n = TelegramNotifier("token123", "chat456")
        assert n.configurado is True

    @patch("luachadinhos.control.notifier.requests.post")
    def test_enviar_ok(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        n = TelegramNotifier("token", "chat")
        assert n.enviar("teste") is True

    @patch("luachadinhos.control.notifier.requests.post")
    def test_enviar_erro_api(self, mock_post):
        mock_post.return_value.json.return_value = {
            "ok": False, "description": "chat not found"
        }
        n = TelegramNotifier("token", "chat")
        assert n.enviar("teste") is False

    @patch("luachadinhos.control.notifier.requests.post")
    def test_enviar_excecao(self, mock_post):
        mock_post.side_effect = Exception("timeout")
        n = TelegramNotifier("token", "chat")
        assert n.enviar("teste") is False

    @patch("luachadinhos.control.notifier.requests.post")
    def test_avisar_inicio(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        n = TelegramNotifier("token", "chat")
        assert n.avisar_inicio("manha", 5) is True
        payload = mock_post.call_args[1]["json"]
        assert "manha" in payload["text"]
        assert "5" in payload["text"]

    @patch("luachadinhos.control.notifier.requests.post")
    def test_avisar_fim(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        n = TelegramNotifier("token", "chat")
        assert n.avisar_fim("noite", 3, 5) is True

    @patch("luachadinhos.control.notifier.requests.post")
    def test_avisar_erro(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        n = TelegramNotifier("token", "chat")
        assert n.avisar_erro("dev", "algo deu errado") is True
