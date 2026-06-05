"""Geração de mensagem WhatsApp — hooks criativos + fechamentos.

Portado do legado (ml_ofertas_categorias.py + shopee_ofertas_categorias.py).
Gera mensagens formatadas para WhatsApp com markdown simples (*bold*, ~strike~).
"""
from __future__ import annotations

import random

from luachadinhos.models.produto import Produto

# ── Hooks criativos por palavra-chave no título ─────────────────────────────
# (palavras-chave, lista de hooks). O primeiro match é usado.
HOOKS_CRIATIVOS: list[tuple[list[str], list[str]]] = [
    (["cueca", "boxer", "slip"], [
        "CHEGA DE LAVAR ROUPA SUJA!",
        "Gaveta vazia de cueca? A gente resolveu!",
        "Semana toda resolvida de uma vez!",
    ]),
    (["calcinha", "lingerie", "sutia"], [
        "De bem com você mesma do lado de dentro!",
        "Conforto + estilo que ninguém vê — mas você sente!",
    ]),
    (["whey", "proteina", "creatina", "suplemento", "pre-treino"], [
        "Músculo não cresce com promessa, não!",
        "Seu treino tá pedindo isso há semanas!",
        "Resultado começa na nutrição!",
    ]),
    (["coleira", "guia", "pet", "cachorro", "gato", "racao"], [
        "Seu melhor amigo merece o melhor!",
        "Porque ele dá amor demais pra receber menos!",
    ]),
    (["camiseta", "camisa", "blusa", "moletom"], [
        "Look novo no armário sem pesar no bolso!",
        "Estilo sem precisar gastar rios de dinheiro!",
    ]),
    (["tenis", "sapato", "sandalia", "calcado", "bota", "chinelo"], [
        "O tênis que tava faltando no look!",
        "Calçado bom que não rasga o bolso? É aqui!",
    ]),
    (["air fryer", "fritadeira", "airfryer"], [
        "Fritura sem culpa chegou!",
        "A cozinha nunca mais vai ser a mesma!",
    ]),
    (["fone", "headphone", "headset", "tws", "bluetooth"], [
        "Som perfeito no ouvido, dinheiro no bolso!",
        "Playlist favorita, preço impossível de ignorar!",
    ]),
    (["perfume", "colonia", "deo parfum"], [
        "Cheiro bom que fica na memória de todo mundo!",
        "Presença marcada antes mesmo de falar!",
    ]),
    (["hidratante", "creme", "serum", "skincare", "protetor", "maquiagem"], [
        "Pele feliz, bolso feliz!",
        "Skincare de qualidade que cabe no orçamento real!",
    ]),
    (["notebook", "computador", "laptop"], [
        "Produtividade no próximo nível!",
        "Trabalho, estudo e lazer num preço só!",
    ]),
    (["celular", "smartphone", "iphone", "galaxy", "xiaomi", "motorola"], [
        "Hora de trocar esse tijolão!",
        "Câmera, bateria e preço que não dá pra ignorar!",
    ]),
    (["brinquedo", "boneca", "lego", "carrinho"], [
        "Presente que garante grito de alegria!",
        "A carinha de feliz que não tem preço — a oferta tem!",
    ]),
    (["cafeteira", "cafe", "nespresso", "expresso"], [
        "Seu café da manhã merecia ser assim!",
        "Barista em casa pagando menos que a lanchonete!",
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


def _hook_criativo(titulo: str, desconto: float) -> str:
    titulo_low = titulo.lower()
    for palavras, hooks in HOOKS_CRIATIVOS:
        if any(p in titulo_low for p in palavras):
            hook = random.choice(hooks)
            if desconto >= 50:
                hook += " [IMPERDIVEL]"
            elif desconto >= 30:
                hook += " [QUENTE]"
            return hook
    # Fallback genérico
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

    destaque = _hook_criativo(p.titulo, desconto)
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
