"""Deduplicação cross-plataforma por similaridade de título.

Remove produtos com títulos muito parecidos (Jaccard >= threshold).
Entre similares, mantém o de maior desconto. Funciona cross ML↔Shopee.
"""
import logging
import re

from luachadinhos.models.produto import Produto

from .tokenizer import garantir_tokens, jaccard

logger = logging.getLogger(__name__)

# Código de modelo = token que mistura letras E números, com >=5 chars
# (ex: 4100nh3zx, gws700, qat00007). Dois produtos com o mesmo código (ou um
# prefixo do outro) são quase certamente o mesmo produto.
_RE_CODIGO_MODELO = re.compile(r"^(?=.*[a-z])(?=.*\d)[a-z0-9]{5,}$")
# Medidas NÃO são código de modelo (110mm, 1300w, 256gb, 50mp, 100ml...)
_RE_MEDIDA_TOK = re.compile(r"^\d+(w|mm|cm|kg|g|ml|l|hz|mah|gb|mb|tb|mp|v|pol)$")


def _codigos_modelo(titulo: str) -> set[str]:
    """Extrai possíveis códigos de modelo do título (exclui medidas)."""
    t = titulo.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return {
        tok for tok in t.split()
        if _RE_CODIGO_MODELO.match(tok) and not _RE_MEDIDA_TOK.match(tok)
    }


def _compartilha_codigo(codigos_p: set[str], codigos_aceitos: set[str]) -> bool:
    """True se algum código de p é igual a, ou prefixo de (ou tem como prefixo),
    um código já aceito. Pega '4100nh3zx' ≈ '4100nh3zx2'."""
    for cp in codigos_p:
        for ca in codigos_aceitos:
            if cp == ca or cp.startswith(ca) or ca.startswith(cp):
                # prefixo só conta se a parte comum for "código-like" (>=5)
                if min(len(cp), len(ca)) >= 5:
                    return True
    return False


def dedup_similares(
    produtos: list[Produto],
    threshold: float = 0.55,
) -> list[Produto]:
    """Remove produtos duplicados, mantendo o de maior desconto.

    Dois produtos são duplicados se: (a) Jaccard de títulos >= threshold, OU
    (b) compartilham um código de modelo (ex: 4100nh3zx) — pega casos que o
    título descreve de formas muito diferentes.

    Args:
        produtos: lista de Produto (pode misturar plataformas).
        threshold: Jaccard mínimo para considerar "mesmo produto".

    Returns:
        Lista filtrada (sem duplicatas).
    """
    ordenados = sorted(produtos, key=lambda p: p.desconto_pct, reverse=True)

    aceitos: list[Produto] = []
    tokens_aceitos: list[frozenset[str]] = []
    codigos_aceitos: set[str] = set()

    for p in ordenados:
        tokens_p = garantir_tokens(p)
        codigos_p = _codigos_modelo(p.titulo)

        # (b) mesmo código de modelo de algum já aceito → duplicado
        if codigos_p and _compartilha_codigo(codigos_p, codigos_aceitos):
            continue

        # (a) título muito similar de algum já aceito → duplicado
        similar = any(
            jaccard(tokens_p, tokens_a) >= threshold for tokens_a in tokens_aceitos
        )
        if similar:
            continue

        aceitos.append(p)
        tokens_aceitos.append(tokens_p)
        codigos_aceitos |= codigos_p

    logger.info("Dedup: %d → %d (threshold=%.2f)", len(produtos), len(aceitos), threshold)
    return aceitos
