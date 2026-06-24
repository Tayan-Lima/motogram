# SESSAO_DEPLOY.md — Retomar Deploy Railway

**Lê este ficheiro primeiro ao iniciar uma nova sessão do OpenCode.**

---

## Contexto

O projecto Motogram GO está pronto para deploy no Railway. A sessão anterior configurou:
- Código: WhiteNoise, Redis Geo Cache, `nixpacks.toml` (GDAL), SECRET_KEY hardening, `Procfile` actualizado
- Tooling: Railway CLI v5.23.0, MCP Railway activo, `RAILWAY_API_KEY` no `.zshrc`

**O deploy ainda NÃO foi executado.** É o próximo passo.

---

## O que está configurado

| Recurso | Localização | Detalhe |
|---------|------------|---------|
| Railway CLI | `~/.railway/bin/railway` | v5.23.0, instalado |
| `RAILWAY_API_KEY` | `~/.zshrc` (env var) | Não exponhas — já está lá, não precisa recriar |
| MCP Railway | `opencode.json` linha 56 | `"enabled": true`, usa `{env:RAILWAY_API_KEY}` |
| Guia de deploy | `docs/DEPLOY_RAILWAY.md` | Leitura obrigatória antes de começar |

---

## Próximos passos (por ordem)

### 1. Ler `docs/DEPLOY_RAILWAY.md`

Tudo está documentado lá. O agente deve ler esse ficheiro e seguir os passos.

### 2. Verificar tooling

```bash
source "$HOME/.railway/env"
railway whoami           # confirma que o CLI está autenticado
```

Se falhar: `railway login` (abre browser para OAuth).

### 3. Criar/deployar no Railway

Seguir `DEPLOY_RAILWAY.md` secção 1 a 4. Resumo rápido:

- **Passo 1**: Criar projecto via browser (`railway.com` → Deploy from GitHub → Tayan-Lima/motogram)
- **Passo 2**: Adicionar PostgreSQL (+ PostGIS) e Redis
- **Passo 3**: Configurar serviços `web` e `bot` com Custom Start Commands e env vars
- **Passo 4**: `railway shell` → `migrate`, `collectstatic`, `createsuperuser`, verificar PostGIS + Redis

### 4. Testar

Seguir checklist na secção 6 do `DEPLOY_RAILWAY.md`.

---

## Ficheiros modificados nesta sessão (já commitados ou prontos para commit)

| Ficheiro | Mudança |
|----------|---------|
| `requirements.txt` | `+ whitenoise` |
| `backend/motogram/settings.py` | SECRET_KEY hardening, WhiteNoise, STATICFILES_STORAGE, CONN_MAX_AGE |
| `Procfile` | `+ migrate && collectstatic && gunicorn --timeout 120` |
| `backend/motoristas/services.py` | Redis Geo: `+import os`, `+_redis_geoadd()` |
| `backend/corridas/services.py` | Redis Geo: `+_redis_geosearch()`, `+ids_filtro` |
| `nixpacks.toml` | NOVO — instala GDAL para PostGIS |
| `docs/DEPLOY_RAILWAY.md` | NOVO — guia completo de deploy |
| `docs/SESSAO_DEPLOY.md` | ESTE FICHEIRO |
| `AGENTS.md` | Actualizado com docs, Redis Geo, contagem de testes |
| `opencode.json` | MCP Railway `enabled: true` |

---

## Variáveis de ambiente necessárias (para o Railway)

O agente deve gerar estas 3 (se ainda não existirem):

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"   # → BOT_SECRET
python -c "import secrets; print(secrets.token_hex(4))"    # → ADMIN_SECRET_PATH
```

Estas vêm de fora:
- `TELEGRAM_TOKEN` — @BotFather
- `HERE_API_KEY` — platform.here.com

O Railway fornece automaticamente:
- `DATABASE_URL` — ao linkar PostgreSQL
- `REDIS_URL` — ao linkar Redis

---

## O que o agente NÃO deve fazer

- ❌ Reinstalar o Railway CLI — já está instalado
- ❌ Recriar o `RAILWAY_API_KEY` — já está no `.zshrc`
- ❌ Alterar `opencode.json` — MCP Railway já activo
- ❌ Implementar Mercado Pago — desactivado para este deploy
- ❌ Expor o token `RAILWAY_API_KEY` no chat ou em logs

---

## Ao concluir o deploy

1. Confirmar que `railway logs` mostra o servidor a correr
2. Confirmar que `/start` no Telegram retorna resposta do bot
3. Actualizar este ficheiro com o estado final
