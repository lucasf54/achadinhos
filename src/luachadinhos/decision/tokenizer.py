"""Tokenizador de títulos e similaridade Jaccard.

Normaliza o título em um frozenset de tokens (sem acentos, minúsculo,
sem pontuação). Usado para dedup, similaridade e classificação de nichos.
"""
from __future__ import annotations

import re
import unicodedata

from luachadinhos.models.produto import Produto

# Stopwords curtas que poluem a comparação
_STOPWORDS = frozenset({
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "com", "sem", "por", "para", "um", "uma", "uns", "umas",
    "o", "a", "os", "as", "que", "ao", "ou",
    "c", "p", "s",  # abreviações comuns
})


def _remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def tokenizar(titulo: str) -> frozenset[str]:
    """Normaliza título em conjunto de tokens únicos."""
    t = _remover_acentos(titulo.lower())
    t = re.sub(r"[^\w\s]", " ", t)
    tokens = {tok for tok in t.split() if tok and tok not in _STOPWORDS and len(tok) > 1}
    return frozenset(tokens)


def garantir_tokens(produto: Produto) -> frozenset[str]:
    """Retorna tokens do produto (calcula e cacheia se necessário)."""
    if produto._tokens is None:
        object.__setattr__(produto, "_tokens", tokenizar(produto.titulo))
    return produto._tokens


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Similaridade de Jaccard entre dois conjuntos de tokens."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0
