# Git e atualização da VM

Repositório: **https://github.com/lucasf54/achadinhos** (privado).
Conta GitHub: `lucasf54` (email `lucasfur@hotmail.com`).
Raiz versionada: `LU_ACHADINHOS_CLAUDE/` (só o sistema 2.0; legado da pasta-mãe fica fora).

## Por que GitHub

Atualizar a VM Oracle vira `git pull` em vez de copiar arquivos na mão por SSH.
Também serve de backup e histórico (dá pra voltar versão se algo quebrar).

## Segurança (IMPORTANTE)

O `.gitignore` protege os segredos — eles **nunca** vão pro GitHub:
`.env`, `secrets/`, `*.key`, `*_cookies.json`, `data/`.
Só o `.env.example` (template sem valores) é versionado.
→ Na VM, criar o `.env` real manualmente (copiar de `.env.example` e preencher).

## Fluxo do dia a dia

### No PC (depois de mexer no código)
```powershell
cd "c:\Users\lucas\OneDrive\Documentos\Afiliados\Lu_achadinhos\LU_ACHADINHOS_CLAUDE"
git add -A
git commit -m "descrição do que mudou"
git push
```

### Na VM Oracle (pra puxar as atualizações)
```bash
cd ~/achadinhos          # onde o repo foi clonado
git pull
# se mudou dependências: pip install -r requirements.txt
# se mudou o schema:     python -m luachadinhos db migrate
```

## Primeira vez na VM (clonar o repo)
```bash
git clone https://github.com/lucasf54/achadinhos.git
cd achadinhos
cp .env.example .env     # depois preencher .env com os segredos reais
# subir Postgres, instalar deps, migrate... (ver docs de deploy quando existir)
```

## Comandos úteis
- `git remote -v` → confirma que aponta pra `achadinhos.git`
- `git status` → mostra o que mudou / se está sincronizado
- `git log --oneline` → histórico de commits

## Autenticação (token)
O push usa o token da conta `lucasf54`, salvo no Git Credential Manager do Windows
(não precisa digitar de novo). Na VM Linux, configurar credential helper ou usar
chave SSH/deploy key na primeira vez.
