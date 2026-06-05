"""Runtime config — monta o objeto `Filtros` de cada disparo.

Camadas, da mais fraca para a mais forte:
  1. Defaults do dataclass `Filtros`.
  2. Defaults de bootstrap do `.env` (Settings).
  3. Tabela `config` do banco (editável sem deploy) — a fonte de verdade em prod.

Funciona SEM banco: se a tabela `config` não estiver acessível, usa só (1)+(2).
Assim dev/testes rodam sem Postgres.
"""
from __future__ import annotations

import logging

from ..models.filtros import Filtros
from .settings import get_settings

log = logging.getLogger(__name__)

# Mapeia chave da tabela `config` -> campo do dataclass Filtros
_CONFIG_PARA_FILTRO = {
    "desconto_real_min":        "desconto_real_min",
    "min_savings_brl":          "min_savings_brl",
    "dedup_threshold":          "dedup_threshold",
    "send_similarity":          "send_similarity",
    "top_por_disparo":          "top_por_disparo",
    "max_por_nicho":            "max_por_nicho",
    "real_discount_window_days":"janela_dias",
    "min_amostras_hist":        "min_amostras_hist",
    "repost_min_days":          "repost_min_days",
    "repost_price_drop_pct":    "repost_price_drop_pct",
}

# Campos que são inteiros no Filtros (o resto vira float)
_CAMPOS_INT = {
    "top_por_disparo", "max_por_nicho", "janela_dias",
    "min_amostras_hist", "repost_min_days",
}


def _filtros_do_env() -> Filtros:
    """Camadas 1+2: defaults do dataclass sobrepostos pelo .env."""
    s = get_settings()
    return Filtros(
        desconto_min=s.filtro_desconto_min,
        avaliacao_min=s.filtro_avaliacao_min,
        avaliacoes_min=s.filtro_avaliacoes_min,
        preco_max=s.filtro_preco_max,
        dedup_threshold=s.dedup_threshold,
        top_por_disparo=s.top_por_disparo,
    )


def _ler_tabela_config() -> dict[str, float]:
    """Lê a tabela `config` do banco. Retorna {} se o banco não estiver acessível."""
    try:
        from ..db.engine import conectar
        with conectar() as conn:
            rows = conn.execute("SELECT key, value FROM config").fetchall()
        return {k: float(v) for k, v in rows}
    except Exception as e:  # banco ausente em dev/teste — degrada para defaults
        log.debug("Tabela config indisponível (%s); usando defaults do .env", e)
        return {}


def carregar_filtros(overrides: dict | None = None) -> Filtros:
    """Monta o `Filtros` efetivo do disparo.

    overrides: dict opcional (ex: vindo do bot/CLI) que vence todas as camadas.
    """
    filtros = _filtros_do_env()

    mudancas: dict = {}
    for chave_cfg, valor in _ler_tabela_config().items():
        campo = _CONFIG_PARA_FILTRO.get(chave_cfg)
        if campo:
            mudancas[campo] = int(valor) if campo in _CAMPOS_INT else float(valor)
    if mudancas:
        filtros = filtros.com(**mudancas)

    if overrides:
        validos = {k: v for k, v in overrides.items() if hasattr(filtros, k)}
        if validos:
            filtros = filtros.com(**validos)

    return filtros
