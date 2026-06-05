# Lu Achadinhos 2.0 🛍️

Reconstrução do sistema de afiliados — de **buscador sob-demanda** para
**esteira de inteligência de ofertas** (coleta 24/7 → banco com histórico →
decisão por score → publicação automática no WhatsApp).

> O código antigo fica na pasta-mãe (`../`) como **referência** de como extrair
> dados do Mercado Livre (Playwright) e da Shopee (API GraphQL). Aqui dentro
> construímos o novo, sem mexer no que já funciona.

---

## Visão

```
COLETA 24/7  →  GUARDA TUDO  →  COMPARA COM O PASSADO  →  DECIDE  →  POSTA SOZINHO
(coletores)     (Postgres)      (oferta REAL vs fake)     (score)    (WhatsApp)
```

## Decisões de produto

- **Distribuição:** 100% automática (regras + score decidem, sem aprovação manual).
- **WhatsApp:** grupos comuns via automação não-oficial (número dedicado/sacrificável).
- **Infra:** robusto mas enxuto — roda no servidor Oracle existente + PostgreSQL.
- **Qualidade:** desconto REAL (anti-fake), não repetir produtos, melhores
  classificações/keywords/nichos, curadoria por score.
- **Telegram:** deixa de ser interface de comando e vira painel de controle
  (alertas, kill-switch, ajuste de regras).

## Roadmap

| Fase | Entrega | Valor |
|---|---|---|
| **0 — Fundação** | Postgres + coletores gravando histórico + anti-repetição | Para de repetir produto |
| **1 — Inteligência** | Anti-fake (desconto real) + score 2.0 + nichos/keywords | Só oferta de verdade |
| **2 — Publicação** | Publisher WhatsApp (throttling humano + kill-switch) | Posta sozinho |
| **3 — Profissional** | Painel web + backup + monitoramento | Operação confiável |
| **4 — Otimização** | Analytics (nicho/horário que converte) | Melhora contínua |

## Stack

Python · PostgreSQL · Playwright (ML) · requests (Shopee) ·
Baileys/Node (WhatsApp, micro-serviço isolado) · FastAPI (painel) ·
Docker Compose (deploy na Oracle).

---

_Status: planejamento. Próximo passo: detalhar a Fase 0._
