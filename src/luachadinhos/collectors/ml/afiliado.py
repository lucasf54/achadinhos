"""Geração de link de afiliado ML — via API oficial (cookies) + fallback manual.

Portado de ml_ofertas_categorias.py. Usa a API interna createLink do ML
com cookies de sessão autenticada. Se falhar, gera link manual com
matt_word/matt_tool.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Credenciais de afiliado (do .env)
MATT_WORD = os.getenv("MATT_WORD", "")
MATT_TOOL = os.getenv("MATT_TOOL", "")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def link_manual(url: str) -> str:
    """Fallback: link com parâmetros matt_word/matt_tool."""
    limpa = url.split("?")[0].split("#")[0]
    return f"{limpa}?matt_word={MATT_WORD}&matt_tool={MATT_TOOL}"


def carregar_cookies(caminho: str | Path) -> str:
    """Carrega cookies do JSON e retorna como string para header Cookie."""
    caminho = Path(caminho)
    if not caminho.exists():
        logger.warning("Arquivo de cookies não encontrado: %s", caminho)
        return ""
    with open(caminho, encoding="utf-8") as f:
        cookies_list = json.load(f)
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)


def renovar_sessao(cookies_str: str) -> str:
    """Renova cookies de sessão visitando a página do link builder."""
    if not cookies_str:
        return cookies_str
    try:
        r = requests.get(
            "https://www.mercadolivre.com.br/afiliados/linkbuilder",
            headers={"User-Agent": _UA, "cookie": cookies_str},
            timeout=15,
            allow_redirects=True,
        )
        cookie_map = {}
        for part in cookies_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookie_map[k.strip()] = v.strip()
        for sc in r.headers.get("set-cookie", "").split(","):
            part = sc.split(";")[0].strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookie_map[k.strip()] = v.strip()
        return "; ".join(f"{k}={v}" for k, v in cookie_map.items())
    except Exception:
        logger.debug("Falha ao renovar sessão", exc_info=True)
        return cookies_str


def gerar_link_oficial(url: str, cookies_str: str) -> tuple[str, bool]:
    """Gera link de afiliado via API createLink do ML.

    Returns:
        Tupla (link, is_oficial). Se a API falhar, retorna link manual.
    """
    url_limpa = url.split("?")[0].split("#")[0]
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://www.mercadolivre.com.br",
        "referer": "https://www.mercadolivre.com.br/afiliados/linkbuilder",
        "user-agent": _UA,
        "cookie": cookies_str,
    }
    try:
        r = requests.post(
            "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink",
            headers=headers,
            json={"urls": [url_limpa], "tag": MATT_WORD},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            urls_list = data.get("urls", data) if isinstance(data, dict) else data
            if isinstance(urls_list, list) and urls_list:
                item = urls_list[0]
                if isinstance(item, dict):
                    link = (
                        item.get("shortUrl")
                        or item.get("short_url")
                        or item.get("affiliateUrl")
                        or item.get("url")
                        or ""
                    )
                    if link:
                        return link, True
    except Exception:
        logger.debug("Falha ao gerar link oficial", exc_info=True)

    return link_manual(url), False
