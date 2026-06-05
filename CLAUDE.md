# CLAUDE.md — Lu Achadinhos 2.0

> Leia este arquivo PRIMEIRO ao abrir o projeto. Ele te põe a par de tudo.

## O que é este projeto

Reconstrução de um sistema de afiliados. O sistema antigo (na pasta-mãe `../`,
arquivos `bot_telegram.py`, `ml_*.py`, `shopee_*.py`) é um **buscador sob-demanda**:
o usuário aperta um botão no Telegram e recebe as ofertas em destaque do momento.
**Problema:** os produtos repetem todo dia, porque não há memória entre execuções.

O **2.0** (esta pasta `LU_ACHADINHOS_CLAUDE/`) é uma **esteira de inteligência de
ofertas**: coleta em 3 disparos/dia → guarda histórico no Postgres → decide por
score (desconto real, anti-fake, anti-repetição, nichos) → publica automático em
grupos de WhatsApp. O código antigo NÃO é modificado — serve só de referência.

## Decisões de produto (já fechadas — não re-perguntar)

- **3 disparos/dia** (manhã/almoço/noite via cron), NÃO 24/7. Operação episódica.
- **Quantidade por disparo ajustável** via tabela `config` (default ~5).
- **Sempre as melhores do momento por score**, sem amarra de tema/nicho por horário.
- **100% automático com kill-switch forte**: antes de cada disparo, avisa no Telegram;
  se o usuário não agir, posta; se apertar PARAR, cancela aquele disparo.
- **WhatsApp via automação não-oficial** (número dedicado/sacrificável, Baileys),
  com throttling humano anti-ban. Telegram vira painel de controle.
- **Infra:** roda na VM Oracle Micro existente (1 GB RAM). A coleta do ML é feita
  SEM navegador (requests no JSON da página /ofertas), o que cabe folgado em 1 GB.
  ARM grátis foi tentada mas a região está sem capacidade ("out of host capacity");
  vira upgrade opcional, não bloqueio.

## Onde está a documentação

- `docs/01-criar-vm-arm-oracle.md` — guia da VM ARM (opcional/bloqueada).
- `docs/02-plano-fase0.md` — **PLANO MESTRE**: schema, fórmulas, e os 24 passos.
- `docs/STATUS.md` — **estado atual e próximo passo concreto**. Leia este.
- Memória do Claude: `../../.claude/projects/.../memory/projeto-lu-achadinhos.md`
  (histórico completo das decisões).

## Estado atual (resumo — detalhe em docs/STATUS.md)

**✅ FASE 0 COMPLETA — Blocos A–F**, 207 testes verdes.
A (Fundação), B (Coletor ML), C (Coletor Shopee), D (Banco), E (Decisão), F (Publicação).
Todos os 24 passos implementados. Ver `docs/STATUS.md` para próximos passos de produção.

## Como rodar

```powershell
cd LU_ACHADINHOS_CLAUDE
.\.venv\Scripts\Activate.ps1            # venv já criado (Python 3.11)
$env:PYTHONIOENCODING = "utf-8"          # PowerShell corrompe acentos sem isto
python -m pytest tests/unit -q           # 23 testes devem passar
python -m luachadinhos --help            # ver a CLI
```

## Restrições do ambiente (importante)

- **Não há Docker nem Postgres** na máquina Windows do usuário. Testes rodam SEM
  banco (a config degrada para defaults). O Postgres real só existe na VM Oracle;
  `python -m luachadinhos db migrate` aplica as tabelas lá.
- **PowerShell corrompe acentos** na exibição — sempre `$env:PYTHONIOENCODING="utf-8"`.
- O coletor ML sem navegador foi verificado por curl de um IP fora do BR; **falta
  validar rodando do IP brasileiro** (PC do usuário ou VM) — é o 1º passo do Bloco B.

## Convenções de código

- Modelo interno = `Produto` (tipado). Só traduz para dict PT-BR na fronteira
  (Excel/WhatsApp/legado), via `models/schema_ptbr.py`. Não espalhar chaves PT-BR.
- Filtros passados por parâmetro (`Filtros` imutável), nunca estado global mutável.
- Cada passo do plano deve vir com teste. Rodar `pytest` antes de seguir.
- Comentários e nomes de domínio em português (o usuário é PT-BR).
