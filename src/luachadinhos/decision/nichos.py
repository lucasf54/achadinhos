"""Classificação de nichos — cascata determinística, sem ML/LLM.

Pipeline: tokens do título → dicionário de nichos → fallback por categoria → "Outros".

O dicionário mapeia palavras-chave no título para um nicho. Tokens são
checados em ordem de prioridade (mais específico primeiro).
"""
from __future__ import annotations

import logging

from luachadinhos.models.produto import Produto

from .tokenizer import garantir_tokens

logger = logging.getLogger(__name__)

# Mapa de tokens → nicho (mais específico primeiro)
# Cada chave pode ser uma palavra ou tupla de palavras (todas devem bater)
MAPA_NICHOS: dict[str, list[str | tuple[str, ...]]] = {
    "Celulares": [
        "celular", "smartphone", "iphone", "galaxy", "xiaomi",
        "motorola", "redmi", "poco",
    ],
    "Informática": [
        "notebook", "laptop", "computador", "pc", "monitor",
        "teclado", "mouse", "ssd", "hd", "pendrive", "webcam",
    ],
    "Áudio": [
        "fone", "headphone", "headset", "earphone", "caixa de som",
        "soundbar", "alto-falante", "microfone", "tws",
    ],
    "TV & Vídeo": [
        "televisor", "tv", "smart tv", "projetor",
    ],
    "Eletrodomésticos": [
        "fritadeira", "air fryer", "cafeteira", "aspirador",
        "ventilador", "liquidificador", "batedeira", "panela",
        "micro-ondas", "fogao", "geladeira", "lavadora",
        "maquina de lavar", "ar condicionado",
    ],
    "Moda": [
        "camiseta", "camisa", "blusa", "moletom", "calca",
        "short", "vestido", "jaqueta", "casaco", "bermuda",
        "saia", "roupa",
    ],
    "Calçados": [
        "tenis", "sapato", "sandalia", "chinelo", "bota",
        "calcado", "sapatenis",
    ],
    "Beleza": [
        "perfume", "maquiagem", "batom", "base", "hidratante",
        "creme", "serum", "skincare", "protetor solar",
        "shampoo", "condicionador", "desodorante",
    ],
    "Esporte": [
        "academia", "whey", "creatina", "proteina", "suplemento",
        "bicicleta", "esteira", "haltere", "caneleira",
    ],
    "Casa & Decoração": [
        "colchao", "travesseiro", "lencol", "cortina",
        "luminaria", "moveis", "sofa", "mesa", "cadeira",
        "organizador", "prateleira",
    ],
    "Pet": [
        "pet", "cachorro", "gato", "racao", "coleira",
        "comedouro", "brinquedo pet", "cama pet",
    ],
    "Bebê": [
        "bebe", "fralda", "carrinho bebe", "mamadeira",
        "chupeta", "berco",
    ],
    "Games": [
        "game", "jogo", "console", "playstation", "xbox",
        "nintendo", "controle", "joystick", "gamer",
    ],
    "Brinquedos": [
        "brinquedo", "boneca", "lego", "quebra-cabeca",
        "carrinho", "pista", "nerf",
    ],
    "Ferramentas": [
        "ferramenta", "furadeira", "parafusadeira", "chave",
        "alicate", "serra", "trena",
    ],
    "Automotivo": [
        "automotivo", "pneu", "oleo motor", "carro",
        "suporte celular carro", "camera re",
    ],
    "Livros": [
        "livro", "livros", "kindle",
    ],
    "Alimentos": [
        "alimento", "chocolate", "cafe", "biscoito",
        "cereal", "azeite",
    ],
    "Saúde": [
        "saude", "vitamina", "remedio", "termometro",
        "oximetro", "massageador",
    ],
}

# Fallback por código de categoria ML
_CATEGORIA_NICHO: dict[str, str] = {
    "MLB1051": "Celulares",
    "MLB1648": "Informática",
    "MLB1000": "Eletrodomésticos",
    "MLB1574": "Casa & Decoração",
    "MLB1276": "Esporte",
    "MLB1132": "Brinquedos",
    "MLB3937": "Calçados",
    "MLB1430": "Beleza",
    "MLB1384": "Bebê",
    "MLB1403": "Alimentos",
    "MLB1071": "Pet",
    "MLB1072": "Pet",
    "MLB1081": "Pet",
    "MLB1144": "Games",
    "MLB1168": "Áudio",
    "MLB187456": "Ferramentas",
    "MLB1747": "Automotivo",
    "MLB3025": "Livros",
}


def classificar_nicho(produto: Produto) -> str:
    """Classifica o nicho do produto (cascata: tokens → mapa → categoria → Outros)."""
    tokens = garantir_tokens(produto)
    texto_lower = " ".join(tokens)

    # 1. Busca no mapa por tokens do título
    for nicho, palavras in MAPA_NICHOS.items():
        for palavra in palavras:
            if isinstance(palavra, tuple):
                if all(p in texto_lower for p in palavra):
                    return nicho
            elif palavra in texto_lower:
                return nicho

    # 2. Fallback por categoria de origem
    cat = produto.categoria.upper()
    if cat in _CATEGORIA_NICHO:
        return _CATEGORIA_NICHO[cat]

    return "Outros"


def aplicar_nichos(produtos: list[Produto]) -> None:
    """Classifica e atribui nicho a todos os produtos (in-place)."""
    contagem: dict[str, int] = {}
    for p in produtos:
        p.nicho = classificar_nicho(p)
        contagem[p.nicho] = contagem.get(p.nicho, 0) + 1

    logger.info("Nichos: %s", dict(sorted(contagem.items(), key=lambda x: -x[1])))
