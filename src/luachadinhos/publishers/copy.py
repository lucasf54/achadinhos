"""Geração de mensagem WhatsApp — hooks criativos + fechamentos.

Portado do legado (ml_ofertas_categorias.py + shopee_ofertas_categorias.py).
Gera mensagens formatadas para WhatsApp com markdown simples (*bold*, ~strike~).
"""
from __future__ import annotations

import random

from luachadinhos.models.produto import Produto

# ── Hooks criativos por NICHO (usa o nicho classificado, não palavra solta) ──
# Evita falsos positivos como "ENFORCA GATO" sendo tratado como produto pet.
HOOKS_POR_NICHO: dict[str, list[str]] = {
    "Pet": [
        "Seu melhor amigo merece o melhor!",
        "Porque ele da amor demais pra receber menos!",
        "Mimo que ele nao vai parar de agradecer!",
    ],
    "Moda": [
        "Look novo no armario sem pesar no bolso!",
        "Estilo sem precisar gastar rios de dinheiro!",
        "Peca que combina com tudo — e cabe no orcamento!",
    ],
    "Calçados": [
        "O tenis que tava faltando no look!",
        "Calcado bom que nao rasga o bolso? E aqui!",
        "Pisando leve no bolso e no estilo!",
    ],
    "Áudio": [
        "Som perfeito no ouvido, dinheiro no bolso!",
        "Playlist favorita, preco impossivel de ignorar!",
    ],
    "Celulares": [
        "Hora de trocar esse tijolao!",
        "Camera, bateria e preco que nao da pra ignorar!",
    ],
    "Informática": [
        "Produtividade no proximo nivel!",
        "Trabalho, estudo e lazer num preco so!",
    ],
    "Eletrodomésticos": [
        "A cozinha nunca mais vai ser a mesma!",
        "Eletrodomestico bom por esse preco? Corre!",
    ],
    "Beleza": [
        "Pele feliz, bolso feliz!",
        "Skincare de qualidade que cabe no orcamento real!",
        "Presenca marcada antes mesmo de falar!",
    ],
    "Esporte": [
        "Resultado comeca na nutricao!",
        "Seu treino ta pedindo isso ha semanas!",
        "Sem desculpa pra pular o treino hoje!",
    ],
    "Brinquedos": [
        "Presente que garante grito de alegria!",
        "A carinha de feliz que nao tem preco — a oferta tem!",
    ],
    "Games": [
        "Level up no setup por esse preco!",
        "Gamer de verdade nao perde essa!",
    ],
    "Bebê": [
        "Pro seu pequeno, so o melhor!",
        "Cuidado de mae com preco que cabe no bolso!",
    ],
    "Casa & Decoração": [
        "Sua casa merecia essa renovacao!",
        "Casa bonita sem gastar uma fortuna!",
    ],
}

# Hooks por palavra-chave (só como REFINAMENTO dentro do nicho certo)
HOOKS_POR_TITULO: list[tuple[list[str], list[str]]] = [
    (["cueca", "boxer", "slip"], [
        "CHEGA DE LAVAR ROUPA SUJA!",
        "Gaveta vazia? A gente resolveu!",
    ]),
    (["whey", "proteina", "creatina", "suplemento"], [
        "Musculo nao cresce com promessa, nao!",
        "Resultado comeca na nutricao!",
    ]),
    (["air fryer", "fritadeira", "airfryer"], [
        "Fritura sem culpa chegou!",
    ]),
    (["perfume", "colonia", "deo parfum"], [
        "Cheiro bom que fica na memoria de todo mundo!",
    ]),
    (["cafeteira", "cafe", "nespresso"], [
        "Seu cafe da manha merecia ser assim!",
    ]),
]

# Fechamentos — sorteados por produto
FECHAMENTOS: list[list[str]] = [
    ["", "Garanta o seu agora:", "{link}", "", "Corre que pode acabar!"],
    ["", "Clica antes de esgotar:", "{link}", "", "Oferta por tempo limitado!"],
    ["", "Aproveita agora:", "{link}", "", "Estoque limitado — corre!"],
    ["", "Pega o seu aqui:", "{link}", "", "Quando acabar, acabou!"],
    ["", "Bora garantir:", "{link}", "", "Não deixa pra depois!"],
]


def _hook_criativo(titulo: str, desconto: float, nicho: str = "") -> str:
    # 1. Tenta hook específico por palavra no título
    titulo_low = titulo.lower()
    for palavras, hooks in HOOKS_POR_TITULO:
        if any(p in titulo_low for p in palavras):
            hook = random.choice(hooks)
            if desconto >= 50:
                hook += " [IMPERDIVEL]"
            elif desconto >= 30:
                hook += " [QUENTE]"
            return hook

    # 2. Tenta hook pelo nicho (evita falsos positivos como "enforca gato")
    if nicho and nicho in HOOKS_POR_NICHO:
        hook = random.choice(HOOKS_POR_NICHO[nicho])
        if desconto >= 50:
            hook += " [IMPERDIVEL]"
        elif desconto >= 30:
            hook += " [QUENTE]"
        return hook

    # 3. Fallback genérico
    if desconto >= 50:
        return "OFERTA IMPERDIVEL"
    elif desconto >= 30:
        return "PROMOCAO QUENTE"
    elif desconto >= 15:
        return "BOA OFERTA DO DIA"
    return "OFERTA DO DIA"


def _fmt_preco(valor: float) -> str:
    """Formata preço em R$ com ponto como separador de milhar."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_mensagem_wa(produto: Produto) -> str:
    """Gera mensagem formatada para WhatsApp a partir de um Produto."""
    p = produto
    desconto = p.desconto_real if p.desconto_real is not None else p.desconto_pct
    link = p.link_afiliado or p.url or ""

    destaque = _hook_criativo(p.titulo, desconto, nicho=p.nicho)
    linhas = [destaque, "", f"*{p.titulo}*", ""]

    # Bloco de preço
    if p.desconto_pct > 0 and p.preco_original > p.preco_atual:
        linhas.append(f"De: ~{_fmt_preco(p.preco_original)}~")
        label = f"{p.desconto_pct:.0f}% OFF"
        linhas.append(f"*{_fmt_preco(p.preco_atual)}* — {label}")
        economia = p.economia_real if p.economia_real is not None else p.economia
        if economia and economia > 0:
            linhas.append(f"Economia de *{_fmt_preco(economia)}*")
    else:
        linhas.append(f"*{_fmt_preco(p.preco_atual)}*")

    # Parcelas
    if p.preco_parcelado and p.preco_parcelado != p.preco_atual and p.preco_parcelado > 0:
        linhas.append(f"Ou parcelado: {_fmt_preco(p.preco_parcelado)}")

    # Frete grátis
    if p.frete_gratis:
        linhas.append("*Frete GRATIS*")

    # Avaliação
    if p.avaliacao:
        aval_txt = f"Avaliacao {p.avaliacao:.1f}"
        if p.n_avaliacoes:
            aval_txt += f" ({p.n_avaliacoes} avaliacoes)"
        elif p.vendas:
            aval_txt += f" ({p.vendas}+ vendidos)"
        linhas.append(aval_txt)

    # Plataforma
    plataforma_label = "Mercado Livre" if p.plataforma == "mercadolivre" else "Shopee"
    linhas.append(f"Via {plataforma_label}")

    # Fechamento
    fechamento = random.choice(FECHAMENTOS)
    linhas += [linha.replace("{link}", link) for linha in fechamento]

    return "\n".join(linhas)


def gerar_mensagens_batch(produtos: list[Produto]) -> None:
    """Gera e atribui mensagem WA para cada produto (in-place)."""
    for p in produtos:
        p.mensagem_wa = gerar_mensagem_wa(p)
