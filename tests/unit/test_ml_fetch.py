"""Testes do fetch ML — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.collectors.ml.fetch import (
    fetch_ofertas,
    montar_url,
    FetchResult,
    _detectar_antibot,
)


class TestMontarUrl:
    def test_url_basica(self):
        url = montar_url("MLB1051")
        assert url == "https://www.mercadolivre.com.br/ofertas?category=MLB1051"

    def test_url_com_preco_max(self):
        url = montar_url("MLB1051", preco_max=500)
        assert "price=*-500.0" in url

    def test_url_paginacao(self):
        url = montar_url("MLB1051", pagina=2)
        assert "_Desde_49" in url

    def test_url_pagina_3(self):
        url = montar_url("MLB1051", pagina=3)
        assert "_Desde_97" in url


class TestDetectarAntibot:
    def test_html_limpo(self):
        assert _detectar_antibot("<html><body>normal</body></html>") == []

    def test_detecta_captcha(self):
        sinais = _detectar_antibot("<html>Por favor complete o captcha</html>")
        assert "captcha" in sinais

    def test_detecta_cloudflare(self):
        sinais = _detectar_antibot("<html>cloudflare challenge</html>")
        assert "cloudflare" in sinais


class TestFetchOfertas:
    @patch("luachadinhos.collectors.ml.fetch.requests.get")
    def test_fetch_ok(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>produtos aqui</body></html>"
        mock_get.return_value = mock_resp

        result = fetch_ofertas("MLB1051")
        assert isinstance(result, FetchResult)
        assert result.status_code == 200
        assert not result.antibot_detectado
        assert result.url == "https://www.mercadolivre.com.br/ofertas?category=MLB1051"

    @patch("luachadinhos.collectors.ml.fetch.requests.get")
    def test_fetch_detecta_antibot(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>captcha required</html>"
        mock_get.return_value = mock_resp

        result = fetch_ofertas("MLB1051")
        assert result.antibot_detectado
        assert "captcha" in result.sinais_antibot

    @patch("luachadinhos.collectors.ml.fetch.requests.get")
    def test_retry_com_erro(self, mock_get):
        import requests as req
        mock_get.side_effect = req.ConnectionError("timeout")

        with pytest.raises(ConnectionError, match="3 tentativas"):
            fetch_ofertas("MLB1051", backoff_base=0.01)
        assert mock_get.call_count == 3
