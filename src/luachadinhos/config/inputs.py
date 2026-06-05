"""Carrega categorias ML e keywords Shopee dos arquivos em inputs/.

Substitui os defaults fixos (só MLB1051) pelo conjunto completo de categorias
que o operador mantém nos .txt. Formato dos arquivos (uma linha por categoria):
    nome;valor        ex: celulares;MLB1051  |  moda;vestuario
Linhas em branco, comentadas (#) ou com numeração inicial são tratadas.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# inputs/ fica na raiz do projeto (3 níveis acima deste arquivo: config/ -> luachadinhos/ -> src/ -> raiz)
_INPUTS_DIR = Path(__file__).resolve().parents[3] / "inputs"


def _parse_linha(linha: str) -> tuple[str, str] | None:
    """Extrai (nome, valor) de uma linha 'nome;valor', tolerando numeração."""
    linha = linha.strip()
    if not linha or linha.startswith("#"):
        return None
    # Remove numeração inicial (ex: "1  moda;vestuario" -> "moda;vestuario")
    partes = linha.split(None, 1)
    conteudo = partes[-1] if len(partes) > 1 and ";" not in partes[0] else linha
    campos = conteudo.split(";")
    if len(campos) >= 2:
        nome = campos[0].strip().lower()
        valor = campos[1].strip().rstrip(";")
        if nome and valor:
            return nome, valor
    return None


def carregar_categorias_ml(arquivo: Path | None = None) -> list[str]:
    """Retorna a lista de códigos de categoria ML (ex: ['MLB1430', 'MLB1384', ...])."""
    arquivo = arquivo or (_INPUTS_DIR / "categorias_cod_ml.txt")
    if not arquivo.exists():
        logger.warning("Arquivo de categorias ML não encontrado: %s", arquivo)
        return []
    codigos: list[str] = []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        par = _parse_linha(linha)
        if par:
            codigos.append(par[1])
    return codigos


def carregar_keywords_shopee(arquivo: Path | None = None) -> list[str]:
    """Retorna a lista de keywords de busca Shopee (ex: ['vestuario', 'chinelos', ...])."""
    arquivo = arquivo or (_INPUTS_DIR / "categorias_keywords_shopee.txt")
    if not arquivo.exists():
        logger.warning("Arquivo de keywords Shopee não encontrado: %s", arquivo)
        return []
    keywords: list[str] = []
    vistos: set[str] = set()
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        par = _parse_linha(linha)
        if par and par[1] not in vistos:
            keywords.append(par[1])
            vistos.add(par[1])
    return keywords
