"""Cliente da API GraphQL de afiliados Shopee.

Autenticação: SHA256(app_id + timestamp + payload + secret).
Portado de shopee_ofertas_categorias.py.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

SHOPEE_API_URL = "https://open-api.affiliate.shopee.com.br/graphql"

# Query de busca por keyword — ordena por desconto (sortType=2)
QUERY_KEYWORD = """
query Search($kw: String!, $limit: Int!, $sort: Int) {
  productOfferV2(keyword: $kw, limit: $limit, sortType: $sort) {
    nodes {
      itemId
      shopId
      productName
      priceMin
      priceMax
      priceDiscountRate
      ratingStar
      sales
      commissionRate
      shopName
      imageUrl
      offerLink
    }
  }
}
"""

SORT_POR_DESCONTO = 2


def _assinar(app_id: str, secret: str, payload_str: str) -> tuple[str, int]:
    """Gera header Authorization com SHA256."""
    timestamp = int(time.time())
    sig = hashlib.sha256(
        f"{app_id}{timestamp}{payload_str}{secret}".encode()
    ).hexdigest()
    auth = f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={sig}"
    return auth, timestamp


def shopee_request(
    query: str,
    variables: dict,
    app_id: str,
    secret: str,
    timeout: int = 30,
) -> dict:
    """Executa uma query GraphQL na API Shopee.

    Returns:
        dict com a resposta JSON da API.

    Raises:
        ConnectionError: se a requisição falhar.
        ValueError: se a API retornar erros GraphQL.
    """
    body = {"query": query, "variables": variables}
    payload_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    auth, ts = _assinar(app_id, secret, payload_str)

    headers = {
        "Content-Type": "application/json",
        "Authorization": auth,
    }

    try:
        r = requests.post(
            SHOPEE_API_URL,
            headers=headers,
            data=payload_str,
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        raise ConnectionError(f"Falha na API Shopee: {exc}") from exc

    if "errors" in data:
        msg = data["errors"][0].get("message", str(data["errors"]))
        raise ValueError(f"Erro GraphQL Shopee: {msg}")

    return data


def buscar_por_keyword(
    keyword: str,
    app_id: str,
    secret: str,
    limite: int = 30,
) -> list[dict]:
    """Busca produtos por keyword na API Shopee.

    Returns:
        Lista de nodes (dicts com itemId, productName, etc.)
    """
    variables = {"kw": keyword, "limit": limite, "sort": SORT_POR_DESCONTO}
    data = shopee_request(QUERY_KEYWORD, variables, app_id, secret)
    nodes = (
        data
        .get("data", {})
        .get("productOfferV2", {})
        .get("nodes", [])
    )
    logger.info("Shopee keyword '%s': %d resultados", keyword, len(nodes))
    return nodes
