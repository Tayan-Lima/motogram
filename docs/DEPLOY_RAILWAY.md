# DEPLOY_RAILWAY.md — Guia de Deploy no Railway

**Motogram GO** — deploy de produção concluído em 2026-06-24.
`DEBUG=False`, HTTPS, WhiteNoise para estáticos, Redis Geo Cache activo, PostGIS 3.7.

**URL**: `https://web-production-ff262.up.railway.app`
**Admin**: `https://web-production-ff262.up.railway.app/g7x9kadm/entrar/`
**Bot**: `@MotoGram_Go_bot` (long-polling)

**Ferramentas:**
- Railway CLI v5.23.0 (`~/.railway/bin/railway`)
- MCP Railway configurado em `opencode.json`
- `RAILWAY_API_KEY` em `.zshrc`

---

## 0. Pré-requisitos — credenciais a obter ANTES do deploy

Gera estas 3 chaves localmente (terminal):

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"   # → BOT_SECRET
python -c "import secrets; print(secrets.token_hex(4))"    # → ADMIN_SECRET_PATH (ex: "a3f9")
```

Obtém estas chaves externas:

| Chave | Onde obter |
|-------|-----------|
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` → guarda o token |
| `HERE_API_KEY` | [platform.here.com](https://platform.here.com) → projecto → REST → API Key |

Tens tudo? Continua.

---

## 1. Criar projecto no Railway

```
1. Acede https://railway.com → Sign Up (usa GitHub)
2. Dashboard → New Project → Deploy from GitHub repo
3. Seleciona o repositório (ex: Tayan-Lima/motogram)
4. Railway detecta automaticamente: Django + Procfile + runtime.txt (Python 3.12)
```

O Railway vai criar um serviço automaticamente. Nos próximos passos vais organizá-lo.

---

## 2. Criar serviços no Railway (ordem correcta)

### 2.1 Serviço PostgreSQL + PostGIS

**IMPORTANTE**: O template padrão `postgres` do Railway NÃO inclui PostGIS. Usar o template `postgis`:

```bash
# Usar CLI (NÃO o link web — cria projecto separado)
railway deploy --template postgis
```

O serviço será criado com nome `PostGIS` e imagem `postgis/postgis:16-master`. A extensão já vem pré-instalada:

```sql
CREATE EXTENSION postgis;   -- deve retornar: extension "postgis" already exists
SELECT PostGIS_Version();    -- 3.7 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
```

### 2.2 Serviço Redis

```
Project Canvas → Create → Database → Add Redis
→ Clica Deploy e aguarda ficar verde
→ Anota o nome do serviço (normalmente "Redis")
```

### 2.3 Serviço Web (Django + Gunicorn)

O Railway criou um serviço ao importar o repo. Configura-o:

```
→ Settings → Name: web
→ Settings → General → Source Repo: seleciona o teu repo (se já não estiver)

→ Settings → Deploy → Custom Start Command:
    cd backend && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn motogram.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

→ Settings → Networking → Generate Domain
→ Anota o domínio (ex: motogram.up.railway.app) — vais precisar dele
```

### 2.4 Serviço Bot (aiogram Telegram)

```
Project Canvas → Create → Empty Service
→ Settings → Name: bot
→ Settings → General → Source Repo: o mesmo repo GitHub
→ Settings → Deploy → Custom Start Command:
    cd bot && python main.py
```

**Nota**: O bot usa long-polling, não webhook. Não precisa de domínio público.
O Railway pode mostrar warning "no open port" — é normal para long-polling. Ignora.

---

## 3. Variáveis de ambiente

Configura as mesmas variáveis nos **dois serviços** (`web` e `bot`).

Em cada serviço: tab **Variables** → **Raw Editor** → cola o bloco abaixo.

**ATENÇÃO**: Substitui os placeholders `????` pelos valores reais que geraste/obtiveste no passo 0.

```yaml
# ═══ Railway — Automáticas ═══
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# ═══ Django ═══
SECRET_KEY=????SUBSTITUIR????
DEBUG=False
ALLOWED_HOSTS=????SUBSTITUIR-PELO-DOMINIO-RAILWAY.up.railway.app

# ═══ URLs ═══
SITE_URL=https://????SUBSTITUIR-PELO-DOMINIO-RAILWAY.up.railway.app
BACKEND_URL=https://????SUBSTITUIR-PELO-DOMINIO-RAILWAY.up.railway.app
CSRF_TRUSTED_ORIGINS=https://????SUBSTITUIR-PELO-DOMINIO-RAILWAY.up.railway.app

# ═══ Telegram ═══
TELEGRAM_TOKEN=????SUBSTITUIR-PELO-TOKEN-DO-BOTFATHER????
BOT_SECRET=????SUBSTITUIR-PELA-CHAVE-GERADA????

# ═══ Admin ═══
ADMIN_SECRET_PATH=????SUBSTITUIR-PELO-PREFIXO-GERADO????

# ═══ HERE Maps ═══
HERE_API_KEY=????SUBSTITUIR-PELA-CHAVE-HERE????

# ═══ Email (console — emails aparecem nos logs, não são enviados) ═══
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# ═══ Pagamentos — DESACTIVADOS para dev ═══
MP_WEBHOOK_SECRET=
MP_ACCESS_TOKEN=
PRECO_ASSINATURA_MENSAL=6900
```

**IMPORTANTE**: Se o nome do serviço PostgreSQL não for "Postgres", ajusta a referência `${{Postgres.DATABASE_URL}}` para o nome real. O Railway é case-sensitive.

---

## 4. Pós-deploy — comandos manuais (via Railway CLI)

O Railway CLI já está instalado. Garante que está autenticado:

```bash
source "$HOME/.railway/env"

# Se pedir Unauthorized, faz login (abre o browser):
railway login

# Confirma autenticação:
railway whoami
```

Conecta ao projecto e abre shell:

```bash
railway link          # seleciona o projecto Motogram
railway shell         # abre shell no serviço web
```

Dentro do shell, executa:

```bash
cd backend

# 1. Verificar se migrações já foram aplicadas (Procfile devia ter feito)
python manage.py migrate --noinput
# Deve mostrar: "No migrations to apply" ou aplicar novas migrações

# 2. Colectar estáticos (WhiteNoise)
python manage.py collectstatic --noinput
# Deve mostrar: "XX static files copied to .../staticfiles"

# 3. Criar superuser admin
python manage.py createsuperuser
# Preenche o email e senha (não pede username)

# 4. Tornar o superuser admin (tipo='admin')
python manage.py shell << 'EOF'
from motoristas.models import Utilizador
u = Utilizador.objects.get(email='teu-email-usado-acima@gmail.com')
u.tipo = 'admin'
u.is_staff = True
u.is_superuser = True
u.save()
print('Admin OK:', u.email, 'tipo:', u.tipo)
EOF

# 5. Verificar PostGIS
python manage.py shell << 'EOF'
import ctypes.util
print('GDAL encontrado:', ctypes.util.find_library('gdal'))
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT PostGIS_Version();')
    print('PostGIS:', c.fetchone()[0])
EOF
# Se falhar: GDAL não instalado ou PostGIS não activado (volta ao passo 2.1)

# 6. Verificar Redis
python manage.py shell << 'EOF'
import os, redis
r = redis.from_url(os.environ['REDIS_URL'])
print('Redis ping:', r.ping())
EOF
# Deve retornar: Redis ping: True

# 7. Sair
exit
```

---

## 5. Domínio próprio (opcional, para produção futura)

```
1. Comprar domínio no Registro.br (ex: motogram.app)
2. Railway → serviço web → Settings → Networking → Custom Domain
3. Adicionar o domínio
4. No Registro.br, criar CNAME: teu-dominio → teu-dominio.up.railway.app
5. Actualizar ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS com o novo domínio
6. Redeploy
```

---

## 6. Verificação final

| # | Teste | URL / Comando | Esperado |
|---|-------|--------------|----------|
| 1 | Web responde | `https://teu-dominio.up.railway.app/` | Landing page carrega |
| 2 | Admin login | `https://teu-dominio.up.railway.app/{PREFIX}/entrar/` | Página de login aparece |
| 3 | Estáticos (CSS/JS) | Abrir landing page → DevTools Network | Sem 404, arquivos servidos com `whitenoise` |
| 4 | Bot responde | Telegram: `/start` | Bot envia mensagem de boas-vindas |
| 5 | Passageiro cria corrida | `https://teu-dominio.up.railway.app/passageiro/` | Formulário carrega, submissão funciona |
| 6 | Motorista recebe notificação | Criar corrida → ver Telegram do motorista | Recebe mensagem com localização + botões |
| 7 | Logs sem erros | `railway logs` e `railway logs -s bot` | Sem `ERROR` ou `CRITICAL` |
| 8 | HTTPS activo | `https://teu-dominio.up.railway.app/admin/` | Cadeado verde, sem warning de segurança |

---

## 7. Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| 502 Bad Gateway | `gunicorn` não arrancou | `railway logs` → ver erro de startup (migrações? env var?) |
| GDAL crash no migrate | Migration `0003` importa GIS sem GDAL | A migration tem `try/except` — se falhar, verificar se o fix está no GitHub |
| PostGIS não disponível | Template `postgres` não tem PostGIS | Usar `railway deploy --template postgis` (NÃO o link web) |
| Bot não responde | `TELEGRAM_TOKEN` errado ou bot bloqueado | `railway logs -s bot` → ver erro de autenticação Telegram |
| Static files 404 | WhiteNoise não configurado | `railway logs` → `python manage.py collectstatic --noinput` |
| Redis não conecta | `REDIS_URL` mal referenciada | Verificar referência `${{Redis.REDIS_URL}}` nas env vars |
| CSRF 403 | `CSRF_TRUSTED_ORIGINS` não inclui o domínio | Adicionar domínio Railway + fazer redeploy |
| Free plan limit (5 serviços) | Serviços fantasmas ocupam slots | Verificar `unmergedChangesCount` no dashboard → Discard changes |
| Railway não actualiza código | Build cache ou `railway redeploy` não puxa | Usar `railway up` (upload directo do código local) |
| "Unknown error" ao aplicar changes | Mudanças conflituosas staged | Discard changes no dashboard, aplicar uma de cada vez |

---

## 8. Comandos úteis no dia-a-dia

```bash
# Ver logs do serviço web
railway logs
railway logs --tail          # seguir em tempo real

# Ver logs do bot
railway logs -s bot
railway logs -s bot --tail

# Redeploy manual (após git push)
railway up

# Shell no serviço
railway shell

# Management commands (dentro do railway shell)
cd backend
python manage.py verificar_assinaturas
python manage.py notificar_vencimento
python manage.py cancelar_corridas_antigas
```

**Alternativa via MCP Railway (dentro do OpenCode):** se o MCP estiver conectado, podes pedir logs, status de serviços e variáveis de ambiente sem usar o terminal. Exemplo: *"mostra os logs do serviço web"* ou *"lista as env vars do serviço bot"*.
