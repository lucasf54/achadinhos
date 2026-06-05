"""Modelo interno `Produto` — a representação tipada que circula no sistema.

Cada coletor (ML, Shopee) produz `Produto`s. O motor de decisão opera sobre
`Produto`s. Só na fronteira (Excel, mensagem WA, código legado) traduzimos para
o dict de chaves em português — ver `schema_ptbr.py`.

Campos calculados pela decisão (desconto_real, score, nicho...) começam None e
são preenchidos ao longo do pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Produto:
    # ── Identidade ───────────────────────────────────────────────────────────
    plataforma: str                      # 'mercadolivre' | 'shopee'
    source_id: str                       # 'MLB123...' | 'itemId_shopId'
    titulo: str

    # ── Preço ────────────────────────────────────────────────────────────────
    preco_atual: float = 0.0             # à vista / PIX
    preco_original: float = 0.0          # riscado
    preco_parcelado: float = 0.0
    desconto_pct: float = 0.0            # desconto do card (propaganda)
    economia: float = 0.0

    # ── Social / qualidade ───────────────────────────────────────────────────
    avaliacao: Optional[float] = None    # nota 0-5
    n_avaliacoes: Optional[int] = None   # ML
    vendas: Optional[int] = None         # Shopee
    comissao_pct: Optional[float] = None
    frete_gratis: Optional[bool] = None
    vendedor: str = ""

    # ── Categorização ────────────────────────────────────────────────────────
    categoria: str = ""                  # rótulo de origem (categoria/keyword)
    nicho: str = ""                      # preenchido pela classificação

    # ── Links / mídia ────────────────────────────────────────────────────────
    url: str = ""
    link_afiliado: str = ""
    link_oficial: bool = False
    imagem: str = ""

    # ── Saída ────────────────────────────────────────────────────────────────
    mensagem_wa: str = ""
    coletado_em: Optional[datetime] = None

    # ── Calculados pela decisão (None até serem preenchidos) ────────────────
    desconto_real: Optional[float] = None
    economia_real: Optional[float] = None
    avg_price_30d: Optional[float] = None
    historico_curto: bool = False
    is_real_discount: Optional[bool] = None
    score: Optional[float] = None
    score_novidade: Optional[float] = None

    # Tokens do título (cache da tokenização p/ dedup/similaridade)
    _tokens: Optional[frozenset[str]] = field(default=None, repr=False)

    @property
    def chave(self) -> tuple[str, str]:
        """Chave natural de identidade (plataforma, source_id)."""
        return (self.plataforma, self.source_id)
