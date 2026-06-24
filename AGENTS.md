# AGENTS.md — Motogram GO

Plataforma de mototáxi para cidades pequenas no Brasil (interior do Amazonas).
Django 5 backend + aiogram 3 Telegram bot + Django Templates mobile-first site.

**Target users**: low-end Android, 3G com 500–2000ms latency, sinal intermitente.

---

## Repo Structure

```
backend/          Django project (manage.py lives here)
  motogram/       Settings, urls, wsgi, mixins.py (BotAuthMixin)
  corridas/       Corridas app — Oferta model p/ negociação InDrive; Avaliacao (1-5★)
                  Ciclo de vida: iniciar, cancelar-motorista, concluir (Haversine)
                  services.py: notificações Telegram em threading.Thread(daemon=True)
  motoristas/     Motoristas + assinaturas; AUTH_USER_MODEL Utilizador
                  backends.py: EmailBackend (login por email)
                  services.py: salvar_localizacao(), gerar_token_telegram(), validar_token_telegram()
  pagamentos/     Mercado Pago Pix (webhook + services)
  site_publico/   Site público (passageiro, landing) + services.py (geocoding HERE Maps)
  admin_mg/       Painel admin custom (NÃO django.contrib.admin) — rota secreta via ADMIN_SECRET_PATH
  templates/      Django templates (passageiro/, motorista/, admin_mg/, site_publico/)
  test_e2e.py     Fluxos completos (passageiro + motorista)
  playwright_tests/  Testes E2E: 18 testes (site passageiro + motorista + admin)
bot/              Processo aiogram 3 standalone (separado do Django)
  main.py         Entry point (long-polling, MemoryStorage FSM)
                  allowed_updates=["message", "callback_query", "edited_message"]
  handlers/       FSM handlers (start, motorista, corridas)
                  safe_tg.py: wrappers seguros p/ edit_text/answer (try/except 3G)
  services.py     HTTP calls → Django API (requests síncrono, nunca aiohttp)
  states.py       aiogram StatesGroup classes
  messages.py     Todas as strings do bot (constantes PT-BR)
  tests/          Bot unit tests (pytest): 36 testes
docs/             ARCHITECTURE.md, CONVENTIONS.md, HANDOFF.md, DESIGN_SYSTEM.md, etc.
```

---

## Commands

**Dois ambientes Python distintos** — usar o intérprete certo:

```bash
# Django backend (venv local: Python 3.14 — deploy Railway: Python 3.12 via runtime.txt)
source venv/bin/activate && cd backend
python manage.py migrate
python manage.py runserver
python manage.py test .                        # tudo: 105 testes (Django unit + integration)
python manage.py test motoristas               # app única
python manage.py test motoristas.tests.test_services.TokenTelegramTest  # classe única
python manage.py test test_e2e                 # só fluxo completo E2E
python manage.py test --verbosity=2

# Testes E2E (Playwright — site passageiro, motorista, admin)
cd backend && python -m pytest playwright_tests/ -v       # 18 testes (precisa da venv activa)

# Bot Telegram (env separado, Python 3.12 via uv)
cd bot && .venv/bin/python main.py           # NÃO usar `python` do sistema

# Testes do bot (precisa de conftest.py que injeta BOT_SECRET, BACKEND_URL, etc.)
cd bot && .venv/bin/python -m pytest tests/ -v            # 36 testes

# Recriar env do bot: cd bot && uv venv && uv pip install aiogram python-dotenv requests requests-mock

# Instalar dependências (se venv estiver limpa)
source venv/bin/activate && pip install -r requirements.txt
```

**Total**: 159 testes (105 Django + 36 bot + 18 Playwright).

**Deploy em**: `https://web-production-ff262.up.railway.app` — Railway (4 serviços: web, bot, PostGIS, Redis).

Sem linter, formatter, typecheck, pre-commit hooks ou CI configurados. `.ruff_cache/` existe — ruff foi usado pontualmente mas não está integrado.

---

## Rules

### Comunicação Bot ↔ Backend
- **Bot nunca toca na DB.** Toda comunicação via HTTP (`bot/services.py` → Django API). Nunca `import` modelos Django no bot.
- **Auth**: header `X-Bot-Secret` (`motogram/mixins.py:BotAuthMixin`), nunca `Authorization: Bearer`.
- **Bot usa `requests` síncrono**, não `aiohttp`. Bloqueia o event loop — tradeoff aceite, `timeout=5`.
- **Django envia notificações Telegram** via `requests.post` a `api.telegram.org` (chamadas de `corridas/services.py` disparadas em `threading.Thread(daemon=True)` nas views), nunca bloqueando a resposta HTTP.
- **Não chamar Telegram API directamente em views** — sempre via `corridas/services.py`.
- **Serviços disponíveis** (`corridas/services.py`): `notificar_motoristas_proximos()` (círculo expansível 5→10→25km + fallback 4 níveis), `notificar_motorista_telegram()`, `notificar_passageiro_telegram()`, `enviar_localizacao_telegram()`, `calcular_distancia_km()` (Haversine), `_limpar_mensagens_antigas()`, `_limpeza_agressiva()`.
- **Serviços motoristas** (`motoristas/services.py`): `salvar_localizacao()`, `gerar_token_telegram()`, `validar_token_telegram()`, `activar_motorista_apos_pagamento()`.
- **Localização de motoristas**: fonte primária = Telegram Live Location (`edited_message`, até 8h, updates ~60s). Fallback = location-on-accept (bot pede GPS ao aceitar corrida se >30min). `salvar_localizacao()` em `motoristas/services.py` actualiza PointField + timestamp.

### Processos & Deploy
- **Dois processos**: `Procfile` → `web` (gunicorn, 2 workers) e `bot` (`python main.py`). Railway.
- **Bot roda apenas em long-polling.** O endpoint `/api/bot/update/` é stub no-op. Não configurar webhook sem substituir o entrypoint.
- **Deploy automático via GitHub**: `git push origin main` dispara deploy no Railway (webhooks). Sempre push depois de commit — Railway detecta e faz build limpa. Se o deploy não actualizar código, usar `railway up` (upload directo).
- **PostGIS no Railway**: usar `railway deploy --template postgis` (CLI, NÃO o link web — cria projecto separado). O template `postgis` usa `postgis/postgis:16-master`. Activar com `CREATE EXTENSION postgis` (já vem pré-instalada).

### User Model & Auth
- **`AUTH_USER_MODEL = 'motoristas.Utilizador'`**. Sempre `get_user_model()` ou import de `motoristas.models`.
- **Custom auth backend**: `motoristas.backends.EmailBackend` (login por email, não username).
- **DRF**: `DEFAULT_AUTHENTICATION_CLASSES` = Session + Token, mas sem `DEFAULT_PERMISSION_CLASSES`. Views gerem auth individualmente.
- **`CorridaStatusView` é pública (sem auth)** — polling do passageiro.
- **`ListarOfertasView`**, **`EscolherMotoristaView`**, **`CancelarCorridaView`** exigem `@login_required` + ownership check.

### Subscription Gate
- `AceitarCorridaView` verifica `motorista.pode_receber_corridas` antes de aceitar. Retorna 403 `{'erro': '...'}`.
- `motorista.pode_receber_corridas` requer: `status_cadastro == 'aprovado'` + `assinatura_activa` + `telegram_id`.
- Outros endpoints (concluir, recusar) verificam apenas ownership, não assinatura.

### Geo / PostGIS
- **PostGIS detection é condicional.** `settings.py` faz probe do GDAL. Sem GDAL: `Motorista.localizacao` fallback para `CharField`, DB fallback para PostgreSQL plain ou SQLite.
- Motorista usa `PointField(srid=4326)`. Usar `ST_DWithin`, `Distance`, `D(km=...)`.
- **Corrida usa `FloatField` para lat/lon** (legacy intencional). Models novos: `PointField`.

### Frontend
- **Sem build step.** Tailwind CSS, Alpine.js, Leaflet.js via CDN. Nunca React, Vue, ou build pipeline.
- **Leaflet.js carrega lazy** — nunca em `<head>`, só quando `abrirMapa()` é chamada. HTML < 15KB.
- **Tiles: OpenStreetMap** (`tile.openstreetmap.org`). **Geocoding: HERE Maps API** (backend, chave nunca no frontend).
- **Não usar Google Maps.** Não usar Nominatim directamente no frontend (viola política de uso). Geocoding/autocomplete sempre via `/api/map/*` endpoints do Django.
- Polling com **backoff adaptativo** (5s → 15s → 30s), nunca intervalo fixo.

### Admin
- **Painel operacional = `admin_mg/`** (custom, sem models.py — opera sobre models de outras apps). Rota secreta via `ADMIN_SECRET_PATH`; login em `<PREFIX>/entrar/`. Em produção usar prefixo opaco. `admin_mg/urls.py` lê `settings.ADMIN_SECRET_PATH` (definido em `settings.py:154` a partir de `os.environ`).
- **`django.contrib.admin` também está montado em `/admin/`** (`settings.py:17`, `motogram/urls.py:7`). Não estender nem adicionar features ao admin do Django — o painel do produto é `admin_mg/`.

---

## Code Quality

### Python / Django
- Remover imports não utilizados antes de finalizar qualquer tarefa.
- Todo model DEVE ter `__str__`.
- Nunca usar `null=True` em CharField ou TextField — usar `blank=True, default=''`.
- Sempre adicionar `select_related`/`prefetch_related` em querysets com FK/M2M que serão acedidos.
- Variáveis de ambiente sem fallback hardcoded — `SECRET_KEY` falha no Django com `ValueError`; `TELEGRAM_TOKEN` e `BOT_SECRET` validados apenas no arranque do bot (`bot/main.py:19-22`).
- `except Exception: pass` proibido — sempre logar com `logger.warning()` ou `logger.debug()`.
- Lógica de negócio em `services.py`. Views só orquestram (validar → service → resposta).
- Endpoints que acedem dados de um utilizador específico devem verificar ownership.
- Erros: sempre `{'erro': 'mensagem legível'}` com HTTP status adequado. Nunca expor internals em 500s.

### aiogram
- Todo handler de mensagem com estado FSM deve ter filtro `F.text` explícito (previne crash com fotos/stickers).
- `router.message.filter(F.chat.type == "private")` em todos os routers — bot não responde em grupos.
- Chamadas à API Telegram via `safe_tg.safe_edit_text()` / `safe_tg.safe_answer()` (em `bot/handlers/safe_tg.py`).
- Nunca logar dados pessoais (CPF, telefone, coordenadas).
- `BOT_SECRET` obrigatório — falhar no startup se ausente.
- Mensagens do bot: constantes em `bot/messages.py`, nunca strings inline.
- Estados FSM: sempre `StatesGroup`, nunca strings soltas.

### JavaScript (Alpine.js + Leaflet)
- Nunca usar `var` — usar `const` ou `let`.
- `x-data` em Alpine sempre como função: `x-data="nome()"` — nunca objecto inline com métodos.
- Leaflet: sempre guardar `this._map` e chamar `this._map.remove()` em `destroy()`.
- Service Worker: sempre incluir `activate` handler com `self.skipWaiting()` + `self.clients.claim()`.

### Segurança
- Webhook do Mercado Pago sempre com validação de assinatura HMAC e verificação de status via API MP.
- `MP_WEBHOOK_SECRET` vazio = rejeitar webhook (não aceitar).
- Nunca calcular valor de pagamento no frontend — sempre `settings.PRECO_ASSINATURA_MENSAL` no backend.
- `user_id` nunca exposto em URLs públicas.
- Nunca retornar `telegram_id` ou tokens em respostas públicas.

### Testes
- Novo endpoint = novo teste de autenticação + happy path + erro 400.
- Novo handler de bot = teste com Update simulado + estado FSM inválido.
- E2E tests usam `@override_settings(BOT_SECRET="test-secret")`.
- Bot tests precisam de env vars (`BOT_SECRET`, `BACKEND_URL`, `SITE_URL`, `TELEGRAM_TOKEN`) — injetadas via `bot/tests/conftest.py` + dependência `requests-mock`.
- Migrations são commitadas (`.gitignore` tem as linhas comentadas). Correr `makemigrations` e commitar os ficheiros gerados.
- Antes de correr testes Playwright: `playwright install` (instala browsers Chromium).

### Performance (crítico para 3G)
- Sempre adicionar `select_related`/`prefetch_related` em views que acedem FK.
- `GZipMiddleware` deve estar presente em `MIDDLEWARE`.
- Campos filtrados frequentemente devem ter `db_index=True`.

---

## Convenções

- **Linguagem**: comentários, strings, commits em PT-BR.
- **Models**: singular PascalCase (`Corrida`, não `Corridas`).
- **URLs**: kebab-case, plural para listas, singular para acções (`/api/corridas/{id}/aceitar/`).
- **Templates**: mobile-first Tailwind CDN. Wrap em `<div class="max-w-md mx-auto min-h-dvh flex flex-col">` com `px-5`. Prefixo `sm:` para desktop.
- **Imports**: stdlib → django → third-party → local (ver `docs/CONVENTIONS.md`).
- **Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:` (ver `docs/CONVENTIONS.md`).

---

## Env Variables

Copiar `.env.example` para `.env`. Pontos críticos:

- `BOT_SECRET` — token interno bot→backend. Gerar: `python -c "import secrets; print(secrets.token_hex(32))"`
- `PRECO_ASSINATURA_MENSAL=6900` — preço em centavos (R$ 69,00)
- `ADMIN_SECRET_PATH` — prefixo opaco da rota admin (default `admin_mg`)
- `DATABASE_URL` — Supabase PostgreSQL (com ou sem PostGIS conforme GDAL)
- `REDIS_URL` — Upstash Redis (opcional; sem ele usa LocMemCache + DB sessions)
- `BACKEND_URL` — usado pelo bot para chamar a API Django
- `HERE_API_KEY` — chave HERE Maps para geocoding (backend only)
- `MP_WEBHOOK_SECRET` — vazio = rejeitar webhooks

Nunca commitar `.env`. `settings.py` imprime hash do `BOT_SECRET` no startup (linha `print` com `_BOT_SECRET_HASH`) — é diagnóstico, não é leak.

---

## Management Commands

```bash
python manage.py cancelar_corridas_antigas   # cancela corridas aguardando >10 min
python manage.py verificar_assinaturas        # desactiva motoristas com assinatura expirada
python manage.py notificar_vencimento         # alerta Telegram p/ assinaturas vencendo em 3 dias
```

---

## Design System

Paleta: primária `#1B7A3D` (verde), secundária `#C75B39` (terracotta), fundo `#FAF7F2`. Padrões completos: `docs/DESIGN_SYSTEM.md`.

---

## Docs Reference

| Doc | Quando ler |
|-----|-----------|
| `docs/ARCHITECTURE.md` | Modelos, endpoints, fluxos de comunicação |
| `docs/HANDOFF.md` | Estado actual, bugs, prioridades, próximo passo |
| `docs/CONVENTIONS.md` | Naming, imports, commits |
| `docs/TESTING.md` | Estratégia de testes, fixtures |
| `docs/DESIGN_SYSTEM.md` | Tokens, paleta, componentes |
| `docs/ROADMAP.md` | Backlog e fases |
| `docs/ONBOARDING.md` | Cadastros (passageiro + motorista) |
| `docs/COMMUNICATION_FLOWS.md` | Fluxos de comunicação entre sistemas |
| `docs/AUDIT_REPORT.md` | Bugs de segurança conhecidos (4 critical + 8 high) |
| `docs/TESTES_MATCHING_GPS.md` | Checklist de 17 testes manuais (matching + GPS) |
| `docs/DEPLOY_REDIS_GEO.md` | Guia de implementação futura (Redis Geo cache — NÃO implementar sem decisão explícita) |
