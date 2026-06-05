"""Filtros de busca/qualidade — passados por parâmetro, sem estado global.

No código legado os filtros viviam em variáveis globais que cada `run_*` mutava
(`global FILTRO_DESCONTO_MIN ...`). Aqui viram um objeto imutável e explícito,
montado uma vez por disparo a partir do .env + tabela `config`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Filtros:
    """Parâmetros de filtragem e seleção de um disparo."""

    desconto_min: int = 20            # % de desconto (do card) mínimo
    avaliacao_min: float = 4.0        # nota mínima (0-5)
    avaliacoes_min: int = 100         # nº mínimo de avaliações/vendas
    preco_max: int = 0                # 0 = sem limite

    # Qualidade / decisão
    desconto_real_min: float = 15.0   # corte anti-fake (% desconto real)
    min_savings_brl: float = 10.0     # economia mínima eliminatória (R$)
    dedup_threshold: float = 0.55     # Jaccard p/ produtos "iguais"
    send_similarity: float = 0.35     # similaridade máx entre enviados no disparo
    top_por_disparo: int = 5          # quantas ofertas por disparo
    max_por_nicho: int = 2            # diversidade por disparo

    # Histórico / repost
    janela_dias: int = 30             # janela da média p/ desconto real
    min_amostras_hist: int = 5        # amostras mín p/ desconto real confiável
    repost_min_days: int = 30         # dias p/ repostar o mesmo produto
    repost_price_drop_pct: float = 10 # queda (%) que libera repost antes do prazo

    def com(self, **mudancas) -> "Filtros":
        """Retorna uma cópia com alguns campos alterados (imutável)."""
        from dataclasses import replace
        return replace(self, **mudancas)
