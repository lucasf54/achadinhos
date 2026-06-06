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

# "Ruído" que NÃO distingue produto: voltagem, cores, palavras de variação.
# Remover antes de comparar faz "Bosch 127v" == "Bosch 220v" e
# "Controle Preto" == "Controle Branco" (mesma oferta, variação diferente).
_RUIDO = frozenset({
    # voltagem
    "127v", "220v", "110v", "12v", "bivolt", "127", "220", "110", "volts", "v",
    # cores
    "preto", "preta", "branco", "branca", "azul", "vermelho", "vermelha",
    "rosa", "verde", "amarelo", "amarela", "cinza", "prata", "dourado",
    "dourada", "roxo", "roxa", "laranja", "marrom", "bege", "carbon", "black",
    "white", "blue", "red", "cor", "cores", "colorido",
    # variação / embalagem genérica
    # (NÃO incluir "kit"/"unidade" — distinguem produto: "Kit 4 Cuecas" ≠ "Cueca")
    "original", "novo", "nova", "modelo", "tipo",
})

# Padrões de token que são puro código/medida (não distinguem o produto real)
_RE_SO_NUMERO = re.compile(r"^\d+$")               # "700", "1300"
_RE_CODIGO = re.compile(r"^[a-z]*\d+[a-z0-9]*$")    # "qat", "gws700", "l550b", "dgs1"
_RE_VOLTAGEM = re.compile(r"^\d+v$")                # "127v", "220v"
_RE_MEDIDA = re.compile(r"^\d+(w|mm|cm|kg|g|ml|l|hz|mah|gb|mp)$")  # "710w", "110mm"


def _remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _eh_ruido(tok: str) -> bool:
    return (
        tok in _STOPWORDS
        or tok in _RUIDO
        or _RE_SO_NUMERO.match(tok) is not None
        or _RE_VOLTAGEM.match(tok) is not None
        or _RE_MEDIDA.match(tok) is not None
    )


def tokenizar(titulo: str) -> frozenset[str]:
    """Normaliza título em conjunto de tokens únicos, removendo ruído
    (voltagem, cores, medidas, códigos) que não distingue o produto."""
    t = _remover_acentos(titulo.lower())
    t = re.sub(r"[^\w\s]", " ", t)
    tokens = {tok for tok in t.split() if tok and len(tok) > 1 and not _eh_ruido(tok)}
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
