"""Testes do kill-switch — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.control.kill_switch import verificar_parar, aguardar_confirmacao


class TestVerificarParar:
    def test_sem_token(self):
        parar, uid = verificar_parar("", "", 0)
        assert parar is False

    @patch("luachadinhos.control.kill_switch.requests.get")
    def test_sem_mensagens(self, mock_get):
        mock_get.return_value.json.return_value = {"result": []}
        parar, uid = verificar_parar("token", "123", 0)
        assert parar is False

    @patch("luachadinhos.control.kill_switch.requests.get")
    def test_mensagem_parar(self, mock_get):
        mock_get.return_value.json.return_value = {
            "result": [{
                "update_id": 100,
                "message": {
                    "chat": {"id": 123},
                    "text": "PARAR",
                },
            }]
        }
        parar, uid = verificar_parar("token", "123", 0)
        assert parar is True
        assert uid == 101

    @patch("luachadinhos.control.kill_switch.requests.get")
    def test_mensagem_outro_chat(self, mock_get):
        mock_get.return_value.json.return_value = {
            "result": [{
                "update_id": 100,
                "message": {
                    "chat": {"id": 999},
                    "text": "PARAR",
                },
            }]
        }
        parar, uid = verificar_parar("token", "123", 0)
        assert parar is False

    @patch("luachadinhos.control.kill_switch.requests.get")
    def test_mensagem_diferente(self, mock_get):
        mock_get.return_value.json.return_value = {
            "result": [{
                "update_id": 100,
                "message": {
                    "chat": {"id": 123},
                    "text": "oi",
                },
            }]
        }
        parar, uid = verificar_parar("token", "123", 0)
        assert parar is False

    @patch("luachadinhos.control.kill_switch.requests.get")
    def test_erro_rede(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        parar, uid = verificar_parar("token", "123", 0)
        assert parar is False


class TestAguardarConfirmacao:
    def test_sem_token_prossegue(self):
        assert aguardar_confirmacao("", "") is True

    @patch("luachadinhos.control.kill_switch.time.sleep")
    @patch("luachadinhos.control.kill_switch.verificar_parar")
    def test_sem_parar_prossegue(self, mock_verificar, mock_sleep):
        mock_verificar.return_value = (False, 1)
        result = aguardar_confirmacao("token", "123", espera_segundos=0)
        assert result is True

    @patch("luachadinhos.control.kill_switch.time.sleep")
    @patch("luachadinhos.control.kill_switch.time.time")
    @patch("luachadinhos.control.kill_switch.verificar_parar")
    def test_parar_cancela(self, mock_verificar, mock_time, mock_sleep):
        # Primeira chamada: limpa updates. Segunda: PARAR detectado.
        mock_verificar.side_effect = [(False, 1), (True, 2)]
        mock_time.side_effect = [0, 0, 5]  # inicio, while check, while check
        result = aguardar_confirmacao("token", "123", espera_segundos=60)
        assert result is False
