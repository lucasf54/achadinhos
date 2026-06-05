"""Fetch da página /ofertas do ML com requests (sem navegador).

Baixa o HTML da página de ofertas por categoria, com retry/backoff
e detecção de anti-bot. Cabe em ~40 MB de RAM (vs ~400 MB do Playwright).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

_SINAIS_ANTIBOT = (
    "captcha", "cloudflare", "challenge-platform",
    "are you a robot", "/cdn-cgi/", "px-captcha",
)


@dataclass(frozen=True)
class FetchResult:
    """Resultado de um fetch de /ofertas."""
    html: str
    status_code: int
    url: str
    antibot_detectado: bool
    sinais_antibot: list[str]


def _detectar_antibot(html: str) -> list[str]:
    baixo = html.lower()
    return [s for s in _SINAIS_ANTIBOT if s in baixo]


def montar_url(categoria: str, pagina: int = 1,
               preco_max: int = 0) -> str:
    """Monta URL de /ofertas para uma categoria ML."""
    base = f"https://www.mercadolivre.com.br/ofertas?category={categoria}"
    if preco_max > 0:
        base += f"&price=*-{float(preco_max)}"
    if pagina > 1:
        offset = (pagina - 1) * 48 + 1
        base += f"&_Desde_{offset}"
    return base


def fetch_ofertas(
    categoria: str,
    pagina: int = 1,
    preco_max: int = 0,
    timeout: int = 30,
    max_tentativas: int = 3,
    backoff_base: float = 2.0,
) -> FetchResult:
    """Baixa a página de ofertas do ML para uma categoria.

    Retries com backoff exponencial. Detecta sinais de anti-bot no HTML.
    """
    url = montar_url(categoria, pagina, preco_max)
    last_exc: Exception | None = None

    for tentativa in range(1, max_tentativas + 1):
        try:
            logger.info("GET %s (tentativa %d/%d)", url, tentativa, max_tentativas)
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            logger.info("HTTP %d | %d bytes", r.status_code, len(r.text))

            sinais = _detectar_antibot(r.text)
            if sinais:
                logger.warning("Sinais de anti-bot detectados: %s", sinais)

            return FetchResult(
                html=r.text,
                status_code=r.status_code,
                url=url,
                antibot_detectado=bool(sinais),
                sinais_antibot=sinais,
            )

        except requests.RequestException as exc:
            last_exc = exc
            if tentativa < max_tentativas:
                espera = backoff_base ** tentativa
                logger.warning(
                    "Falha na tentativa %d: %s — retry em %.1fs",
                    tentativa, exc, espera,
                )
                time.sleep(espera)

    raise ConnectionError(
        f"Falha ao baixar {url} após {max_tentativas} tentativas: {last_exc}"
    )
