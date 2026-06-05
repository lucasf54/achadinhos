"""Testes da API Shopee — sem rede (mockado)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.collectors.shopee.api import (
    _assinar,
    buscar_por_keyword,
    shopee_request,
)


class TestAssinar:
    def test_retorna_auth_e_timestamp(self):
        auth, ts = _assinar("app123", "secret456", '{"query":"test"}')
        assert auth.startswith("SHA256 Credential=app123, Timestamp=")
        assert "Signature=" in auth
        assert ts > 0

    def test_assinaturas_diferentes_com_payload_diferente(self):
        a1, _ = _assinar("app", "sec", '{"a":1}')
        a2, _ = _assinar("app", "sec", '{"a":2}')
        # Signatures devem ser diferentes
        sig1 = a1.split("Signature=")[1]
        sig2 = a2.split("Signature=")[1]
        assert sig1 != sig2


class TestShopeeRequest:
    @patch("luachadinhos.collectors.shopee.api.requests.post")
    def test_request_ok(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"productOfferV2": {"nodes": []}}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        data = shopee_request("query { test }", {}, "app", "sec")
        assert "data" in data

    @patch("luachadinhos.collectors.shopee.api.requests.post")
    def test_graphql_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errors": [{"message": "Invalid query"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="Invalid query"):
            shopee_request("query { bad }", {}, "app", "sec")

    @patch("luachadinhos.collectors.shopee.api.requests.post")
    def test_connection_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(ConnectionError, match="Falha na API Shopee"):
            shopee_request("query { test }", {}, "app", "sec")


class TestBuscarPorKeyword:
    @patch("luachadinhos.collectors.shopee.api.shopee_request")
    def test_retorna_nodes(self, mock_req):
        mock_req.return_value = {
            "data": {
                "productOfferV2": {
                    "nodes": [{"itemId": 1, "productName": "Fone"}]
                }
            }
        }
        nodes = buscar_por_keyword("fone", "app", "sec", limite=10)
        assert len(nodes) == 1
        assert nodes[0]["productName"] == "Fone"

    @patch("luachadinhos.collectors.shopee.api.shopee_request")
    def test_resposta_vazia(self, mock_req):
        mock_req.return_value = {"data": {"productOfferV2": {"nodes": []}}}
        nodes = buscar_por_keyword("xyz", "app", "sec")
        assert nodes == []
