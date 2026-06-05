# Passo a passo — Criar VM ARM grátis na Oracle Cloud

> Objetivo: substituir a VM `VM.Standard.E2.1.Micro` (1 GB RAM, insuficiente)
> por uma **ARM Ampere A1** do Always Free (até 4 OCPU / 24 GB RAM, grátis pra sempre).

## Recomendação de tamanho
Concentrar todo o pacote free numa VM só: **4 OCPUs + 24 GB RAM**.
Quanto mais RAM, mais folga pro Chromium (Playwright).

## Passos

1. **cloud.oracle.com** → ☰ → **Compute** → **Instances** → confirmar a **região** correta.
2. **Create instance**.
3. **Name:** `lu-achadinhos-arm`.
4. **Image and shape** → **Edit**:
   - **Change image** → Canonical **Ubuntu 22.04** → confirmar.
   - **Change shape** → aba **Ampere** → `VM.Standard.A1.Flex`:
     - OCPUs = **4**, Memory = **24 GB** (automático) → **Select shape**.
5. **Networking:** VCN nova (padrão) + **Assign public IPv4 = Yes**.
6. **Add SSH keys:**
   - "Generate a key pair for me" → **Save private key** (guardar o `.key`!).
   - ou "Paste public keys" e colar a chave existente.
7. **Create** → aguardar status **Running** → anotar **Public IP**.

## Se der "Out of host capacity"
Não é erro da conta — as ARM são disputadas. Tente:
- outro **Availability Domain** (seletor na tela),
- tamanho menor: **2 OCPU / 12 GB** (ainda 12× melhor que a Micro),
- novamente mais tarde / outro horário.

## Anotar quando terminar
- [ ] Criou? (ou travou?)
- [ ] Shape final conseguido (4/24, 2/12...)
- [ ] Public IP
- [ ] Caminho + nome da chave SSH (.key)

## Próximo passo
Conectar via SSH e preparar a VM (Docker, Python, Postgres, Playwright).
Ver `02-preparar-vm.md` (a criar).
