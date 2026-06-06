"""Engine de decisão — pipeline completo de seleção de ofertas.

Pipeline (do plano):
    coleta tudo → dedup → desconto real + nicho → anti-fake →
    anti-repetição → score → top-N com diversidade (máx 2/nicho)

Modos de operação:
- Com banco (conn != None): usa histórico real para desconto real e anti-repetição.
- Sem banco (conn == None): usa fallback (desconto do card, sem anti-repetição).
  Útil para dry-run e bootstrap.
"""
from __future__ import annotations

import logging
from typing import Any

from luachadinhos.db.historico import Stats30d, stats_preco_30d_batch
from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto

from .anti_fake import calcular_desconto_real, filtrar_anti_fake
from .dedup import dedup_similares
from .nichos import aplicar_nichos
from .score import calcular_score

logger = logging.getLogger(__name__)


def _aplicar_desconto_real_batch(
    produtos: list[Produto],
    product_ids: dict[str, int] | None,
    conn: Any | None,
    filtros: Filtros,
) -> None:
    """Calcula desconto real para todos os produtos."""
    if conn is None or product_ids is None:
        # Sem banco: fallback
        for p in produtos:
            calcular_desconto_real(p, stats=None, min_amostras=filtros.min_amostras_hist)
        return

    # Batch: busca stats de todos de uma vez
    ids = [pid for key, pid in product_ids.items() if pid]
    stats_map = stats_preco_30d_batch(conn, ids, janela_dias=filtros.janela_dias) if ids else {}

    for p in produtos:
        chave = f"{p.plataforma}:{p.source_id}"
        pid = product_ids.get(chave)
        stats = stats_map.get(pid) if pid else None
        calcular_desconto_real(p, stats=stats, min_amostras=filtros.min_amostras_hist)


# "Tipo de produto" — captura casos que o dedup por título não pega, como
# 2 controles de Xbox descritos de formas diferentes. Cada entrada: (rótulo do
# tipo, conjunto de termos que TODOS devem aparecer no título). Mais específico
# primeiro. Só 1 produto por tipo é publicado no mesmo disparo.
_TIPOS_PRODUTO: list[tuple[str, frozenset[str]]] = [
    ("controle-xbox",      frozenset({"controle", "xbox"})),
    ("controle-ps5",       frozenset({"controle", "ps5"})),
    ("controle-ps4",       frozenset({"controle", "ps4"})),
    ("joystick-ps5",       frozenset({"joystick", "ps5"})),
    ("joystick-ps4",       frozenset({"joystick", "ps4"})),
    ("esmerilhadeira",     frozenset({"esmerilhadeira"})),
    ("liquidificador",     frozenset({"liquidificador"})),
    ("air-fryer",          frozenset({"fryer"})),
    ("cafeteira",          frozenset({"cafeteira"})),
    ("fone-bluetooth",     frozenset({"fone", "bluetooth"})),
]


def _tipo_produto(p: Produto) -> str | None:
    """Detecta o 'tipo' do produto pelo título (ou None se não casar nenhum)."""
    from .tokenizer import garantir_tokens
    tokens = garantir_tokens(p)
    for rotulo, termos in _TIPOS_PRODUTO:
        if termos <= tokens:  # todos os termos presentes
            return rotulo
    return None


# Palavras de "tipo de oferta" que costumam abrir o título antes da marca real.
_PREFIXO_GENERICO = frozenset({
    "alimento", "racao", "kit", "perfume", "tenis", "fritadeira", "controle",
    "fone", "smartphone", "celular", "rel", "relogio", "smartwatch", "cafeteira",
})


def _assinatura_marca(p: Produto) -> str:
    """Assinatura 'marca + nicho': 1ª palavra significativa (a marca) + o nicho.

    Ex: as 3 'Premier ... Hipoalergênico' (todas nicho Pet) → 'premier|Pet',
    então só 1 entra no disparo. Mas 'Samsung' celular e 'Samsung' TV ficam
    'samsung|Celulares' e 'samsung|TV & Vídeo' → ambos podem entrar (nichos
    diferentes). Pula prefixos genéricos (Ração, Kit) pra chegar na marca real.
    """
    import re
    import unicodedata
    from .tokenizer import tokenizar
    t = unicodedata.normalize("NFKD", p.titulo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s]", " ", t)
    toks_validos = tokenizar(p.titulo)
    validos = [w for w in t.split() if w in toks_validos]
    i = 0
    while i < len(validos) and validos[i] in _PREFIXO_GENERICO:
        i += 1
    if i >= len(validos):
        return ""
    marca = validos[i]
    return f"{marca}|{p.nicho or 'Outros'}"


def _selecionar_top_n_diverso(
    produtos: list[Produto],
    top_n: int,
    max_por_nicho: int,
) -> list[Produto]:
    """Seleciona top-N com diversidade por nicho E por tipo de produto.

    Ordena por score decrescente. Aceita até max_por_nicho do mesmo nicho,
    e no máximo 1 do mesmo "tipo" (ex: 1 controle-xbox, 1 esmerilhadeira).
    """
    ordenados = sorted(produtos, key=lambda p: p.score or 0, reverse=True)

    selecionados: list[Produto] = []
    contagem_nicho: dict[str, int] = {}
    tipos_vistos: set[str] = set()
    marcas_vistas: set[str] = set()

    for p in ordenados:
        nicho = p.nicho or "Outros"
        if contagem_nicho.get(nicho, 0) >= max_por_nicho:
            continue
        # Máx 1 por tipo de produto (controle xbox, esmerilhadeira, etc)
        tipo = _tipo_produto(p)
        if tipo is not None and tipo in tipos_vistos:
            continue
        # Máx 1 por marca+linha (evita 3 "Premier Hipoalergênico" no disparo)
        marca = _assinatura_marca(p)
        if marca and marca in marcas_vistas:
            continue
        selecionados.append(p)
        contagem_nicho[nicho] = contagem_nicho.get(nicho, 0) + 1
        if marca:
            marcas_vistas.add(marca)
        if tipo is not None:
            tipos_vistos.add(tipo)
        if len(selecionados) >= top_n:
            break

    return selecionados


def decidir(
    produtos: list[Produto],
    filtros: Filtros | None = None,
    conn: Any | None = None,
    product_ids: dict[str, int] | None = None,
    postados_ids: set[str] | None = None,
) -> list[Produto]:
    """Pipeline completo de decisão.

    Args:
        produtos: lista de Produto coletados (todas as fontes).
        filtros: parâmetros de filtragem.
        conn: conexão psycopg (None para modo offline/dry-run).
        product_ids: mapa "plataforma:source_id" → product.id no banco.
        postados_ids: set de "plataforma:source_id" já postados recentemente.

    Returns:
        Lista final selecionada (top-N, diversa por nicho).
    """
    if filtros is None:
        filtros = Filtros()

    if not produtos:
        return []

    logger.info("Decisão: %d produtos de entrada", len(produtos))

    # 1. Dedup por similaridade de título
    candidatos = dedup_similares(produtos, threshold=filtros.dedup_threshold)

    # 2. Classificar nichos
    aplicar_nichos(candidatos)

    # 3. Desconto real (com ou sem banco)
    _aplicar_desconto_real_batch(candidatos, product_ids, conn, filtros)

    # 4. Anti-fake
    candidatos = filtrar_anti_fake(
        candidatos,
        desconto_real_min=filtros.desconto_real_min,
        min_savings_brl=filtros.min_savings_brl,
    )

    # 5. Anti-repetição (se temos info de postados)
    if postados_ids:
        antes = len(candidatos)
        candidatos = [
            p for p in candidatos
            if f"{p.plataforma}:{p.source_id}" not in postados_ids
        ]
        logger.info("Anti-repetição: %d → %d", antes, len(candidatos))

    # 6. Score 2.0
    for p in candidatos:
        calcular_score(p)

    # 7. Top-N com diversidade por nicho
    selecionados = _selecionar_top_n_diverso(
        candidatos,
        top_n=filtros.top_por_disparo,
        max_por_nicho=filtros.max_por_nicho,
    )

    logger.info(
        "Decisão final: %d selecionados de %d candidatos",
        len(selecionados), len(candidatos),
    )
    return selecionados
