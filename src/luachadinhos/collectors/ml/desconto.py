"""Cálculo de desconto, economia e comissão para produtos ML.

Porta a lógica robusta do legado (ml_ofertas_categorias.py):
- Recalcula desconto se o preço original falta
- Garante economia >= 0
- Comissão por categoria (tabela do programa de afiliados ML)
"""
from __future__ import annotations

from luachadinhos.models.produto import Produto

# Tabela de comissões ML por palavra-chave no título/categoria.
# Fonte: programa de afiliados ML (valores aproximados, atualizados 2025).
COMISSOES: dict[str, float] = {
    "televisor": 9.5, "tv": 9.5,
    "notebook": 5.0, "computador": 5.0, "laptop": 5.0,
    "celular": 5.0, "smartphone": 5.0, "iphone": 5.0,
    "tablet": 5.0,
    "câmera": 5.0,
    "fone": 9.5, "headphone": 9.5, "headset": 9.5, "áudio": 9.5,
    "ar condicionado": 5.0, "geladeira": 5.0, "lavadora": 5.0,
    "máquina de lavar": 5.0, "micro-ondas": 5.0, "fogão": 5.0,
    "fritadeira": 9.5, "air fryer": 9.5, "cafeteira": 9.5,
    "aspirador": 9.5, "ventilador": 9.5, "eletrodoméstico": 9.5,
    "móveis": 9.5, "colchão": 9.5,
    "roupa": 12.0, "moda": 12.0, "calçado": 12.0, "tênis": 12.0,
    "beleza": 16.0, "perfume": 16.0, "cosméticos": 16.0,
    "saúde": 12.0, "esporte": 12.0, "brinquedo": 12.0,
    "livro": 9.5,
    "game": 5.0, "jogo": 5.0,
    "automóvel": 5.0, "pneu": 5.0,
    "ferrament": 9.5,
    "pet": 9.5, "cachorro": 9.5, "gato": 9.5,
    "alimento": 9.5,
    "bebê": 12.0,
}

COMISSAO_DEFAULT = 9.5


def calcular_comissao(titulo: str, categoria: str = "") -> float:
    """Retorna % de comissão com base no título e categoria."""
    texto = f"{titulo} {categoria}".lower()
    for chave, pct in COMISSOES.items():
        if chave in texto:
            return pct
    return COMISSAO_DEFAULT


def aplicar_desconto_economia(produto: Produto) -> Produto:
    """Garante consistência de desconto/economia e atribui comissão.

    Regras (portadas do legado):
    - Se preço original <= 0 e tem desconto_pct → recalcula original
    - Se preço original < atual → iguala
    - Se original > atual e desconto_pct == 0 → recalcula desconto
    - Economia é sempre >= 0
    - Comissão vem da tabela por palavra-chave
    """
    p = produto

    if p.preco_original <= 0 and p.desconto_pct > 0:
        p.preco_original = round(p.preco_atual / (1 - p.desconto_pct / 100), 2)
    elif p.preco_original <= 0:
        p.preco_original = p.preco_atual

    if p.preco_original < p.preco_atual:
        p.preco_original = p.preco_atual

    if p.preco_original > p.preco_atual and p.desconto_pct == 0:
        p.desconto_pct = round((1 - p.preco_atual / p.preco_original) * 100, 1)

    p.economia = max(round(p.preco_original - p.preco_atual, 2), 0)
    p.comissao_pct = calcular_comissao(p.titulo, p.categoria)

    return p
