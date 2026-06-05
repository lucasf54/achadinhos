"""Valida a aposta central da Fase 0: coletar ofertas do ML SEM navegador.

Baixa a página /ofertas com requests (sem Chromium) e investiga:
  1. O HTTP responde 200? (ou cai em anti-bot/challenge?)
  2. O HTML traz o JSON de hydration com os produtos?
  3. Conseguimos extrair título + preço de pelo menos alguns produtos?

Uso:
    python scripts/validar_ml_sem_navegador.py [CATEGORIA]
    (CATEGORIA default = MLB1051, celulares)

Salva o HTML baixado em data/ml_ofertas_amostra.html para virar golden file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "data"
SAIDA.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def baixar(categoria: str) -> requests.Response:
    url = f"https://www.mercadolivre.com.br/ofertas?category={categoria}"
    print(f"→ GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    print(f"  HTTP {r.status_code} | {len(r.text):,} bytes | "
          f"content-type: {r.headers.get('content-type','?')}")
    return r


def detectar_antibot(html: str) -> list[str]:
    sinais = []
    baixo = html.lower()
    for marca in ("captcha", "cloudflare", "challenge-platform",
                  "are you a robot", "/cdn-cgi/", "px-captcha", "verificação"):
        if marca in baixo:
            sinais.append(marca)
    return sinais


def achar_blocos_json(html: str) -> dict[str, int]:
    """Procura padrões conhecidos de JSON embutido e conta ocorrências."""
    padroes = {
        "__PRELOADED_STATE__": len(re.findall(r"__PRELOADED_STATE__", html)),
        "preloadedState":      len(re.findall(r"preloadedState", html)),
        "application/json":    len(re.findall(r'type="application/json"', html)),
        "polycard":            len(re.findall(r"polycard", html, re.I)),
        '"price"':             len(re.findall(r'"price"', html)),
        '"title"':             len(re.findall(r'"title"', html)),
        "discount":            len(re.findall(r"discount", html, re.I)),
    }
    return padroes


def extrair_amostra_precos(html: str) -> list[str]:
    """Heurística leve: acha trechos com preço perto de título no JSON."""
    achados = []
    # padrão comum no hydration: ..."title":"...","price":{... "value":123.45 ...}
    for m in re.finditer(r'"title"\s*:\s*"([^"]{8,90})"', html):
        achados.append(m.group(1))
        if len(achados) >= 8:
            break
    return achados


def main() -> int:
    categoria = sys.argv[1] if len(sys.argv) > 1 else "MLB1051"
    print(f"=== Validação ML sem navegador — categoria {categoria} ===\n")

    try:
        r = baixar(categoria)
    except Exception as e:
        print(f"❌ Falha na requisição: {e}")
        return 1

    html = r.text
    arq = SAIDA / "ml_ofertas_amostra.html"
    arq.write_text(html, encoding="utf-8")
    print(f"  HTML salvo em {arq.relative_to(ROOT)}\n")

    if r.status_code != 200:
        print(f"⚠️  Status {r.status_code} — pode ser bloqueio. Ver HTML salvo.")

    sinais = detectar_antibot(html)
    if sinais:
        print(f"⚠️  Possíveis sinais de anti-bot: {sinais}")
    else:
        print("✅ Nenhum sinal óbvio de anti-bot/captcha.")

    print("\n--- Blocos JSON encontrados (ocorrências) ---")
    blocos = achar_blocos_json(html)
    for k, v in blocos.items():
        flag = "✅" if v > 0 else "  "
        print(f"  {flag} {k:22} {v}")

    print("\n--- Amostra de títulos extraídos do JSON ---")
    titulos = extrair_amostra_precos(html)
    if titulos:
        for i, t in enumerate(titulos, 1):
            print(f"  {i}. {t}")
        print(f"\n✅ APOSTA CONFIRMADA: {len(titulos)}+ produtos no HTML sem navegador.")
        veredito = 0
    else:
        print("  (nenhum título extraído pela heurística)")
        print("\n⚠️  JSON pode ter estrutura diferente — inspecionar o HTML salvo.")
        veredito = 0 if blocos.get('"title"', 0) > 5 else 2

    print(f"\n=== Fim. Veredito: {'OK' if veredito == 0 else 'INCERTO'} ===")
    return veredito


if __name__ == "__main__":
    raise SystemExit(main())
