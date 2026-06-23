# AGENTS.md — Motogram GO

Plataforma de mototáxi para cidades pequenas no Brasil (interior do Amazonas).
Django 5 backend + aiogram 3 Telegram bot + Django Templates mobile-first site.

**Target users**: low-end Android, 3G com 500–2000ms latency, sinal intermitente.

> **Fonte canónica.** Este ficheiro é a fonte de verdade. `docs/AGENTS.md` é espelho — se divergir, confia neste (root).

---

## Repo Structure

```
backend/          Django project (manage.py lives here)
  motogram/       Settings, urls, wsgi, mixins.py (BotAuthMixin)
  corridas/       Corridas app (models, views, services) — Oferta model p/ negociação InDrive; Avaliacao model (1-5★)
                  Ciclo de vida completo: iniciar, cancelar-motorista, concluir com Haversine
  motoristas/     Motoristas + assinaturas (also owns AUTH_USER_MODEL Utilizador)
                  backends.py: EmailBackend (login por email, não username)
  pagamentos/     Mercado Pago Pix (webhook + services)
  site_publico/   Site público (passageiro, landing) + services.py (geocoding HERE Maps)
  admin_mg/       Painel admin custom (NOT Django.contrib.admin) — rota secreta via ADMIN_SECRET_PATH
  templates/      Django templates (passageiro/, motorista/, admin_mg/)
  test_e2e.py     Fluxos completos (passageiro + motorista)
  playwright_tests/  Testes E2E (Playwright): 18 testes (site passageiro + motorista + admin)
bot/              Processo aiogram 3 standalone (separado do Django)
  main.py         Entry point (long-polling, MemoryStorage FSM)
  handlers/       FSM handlers (start, motorista, corridas) — inclui iniciar:, cancelar_motorista:, avaliar_p:, pular_comentario:
  services.py     HTTP calls → Django API (requests síncrono, nunca aiohttp)
                  Métodos: iniciar_corrida(), cancelar_corrida_motorista(), avaliar_passageiro(), limpar_mensagens()
  states.py       aiogram StatesGroup classes — inclui aguardando_comentario_avaliacao
  messages.py     Todas as strings do bot (constantes PT-BR)
  tests/          Bot unit tests (pytest): 26 testes (services + handlers)
docs/             ARCHITECTURE.md, CONVENTIONS.md, HANDOFF.md, CHECKLIST_TESTES_MANUAIS.md, etc.
```

---

## Commands

**Dois ambientes Python distintos** — usar o intérprete certo:

```bash
# Django backend (venv: /home/gamer/Área/ ou repo venv/ — ambos Python 3.14)
source /home/gamer/Área/bin/activate && cd backend       # ou: source venv/bin/activate
python manage.py migrate
python manage.py runserver
python manage.py test .                        # tudo: apps + test_e2e (~82 testes)
python manage.py test motoristas               # app única
python manage.py test motoristas.tests.test_services.TokenTelegramTest  # classe única
python manage.py test test_e2e                 # só fluxo completo E2E
python manage.py test site_publico.tests.test_map  # 12 testes geocoding HERE
python manage.py test --verbosity=2

# Testes E2E (Playwright — site passageiro, motorista, admin)
cd backend && python -m pytest playwright_tests/ -v       # 18 testes

# Bot Telegram (env separado, Python 3.12 via uv)
cd bot && .venv/bin/python main.py           # NÃO usar `python` do sistema

# Testes do bot
cd bot && .venv/bin/python -m pytest tests/ -v            # 26 testes (services + handlers)

# Recriar env do bot: cd bot && uv venv && uv pip install aiogram python-dotenv requests requests-mock

# Instalar dependências (se venv estiver limpa)
source /home/gamer/Área/bin/activate && pip install -r requirements.txt
```

O `requirements.txt` na raiz cobre todas as dependências Django + aiogram. O env separado do bot é opcional mas recomendado para desenvolvimento paralelo.

Sem linter, formatter, typecheck, pre-commit hooks ou CI configurados. `.ruff_cache/` existe — ruff foi usado pontualmente mas não está integrado.

---

## Rules

### Comunicação Bot ↔ Backend
- **Bot nunca toca na DB.** Toda comunicação via HTTP (`bot/services.py` → Django API). Nunca `import` modelos Django no bot.
- **Auth**: header `X-Bot-Secret` (`motogram/mixins.py:BotAuthMixin`), nunca `Authorization: Bearer`.
- **Bot usa `requests` síncrono**, não `aiohttp`. Bloqueia o event loop — tradeoff aceite, `timeout=5`.
- **Django envia notificações Telegram** via `requests.post` a `api.telegram.org` (chamadas de `corridas/services.py` disparadas em `threading.Thread(daemon=True)` nas views), nunca bloqueando a resposta HTTP.
- **Não chamar Telegram API directamente em views** — sempre via `corridas/services.py`.
- **Serviços disponíveis**: `notificar_motoristas_proximos()`, `notificar_motorista_telegram()`, `notificar_passageiro_telegram()`, `enviar_localizacao_telegram()`, `calcular_distancia_km()` (Haversine), `_limpar_mensagens_antigas()`, `_limpeza_agressiva()`.

### Processos & Deploy
- **Dois processos**: `Procfile` → `web` (gunicorn, 2 workers) e `bot` (`python main.py`). Railway.
- **Bot roda apenas em long-polling.** O endpoint `/api/bot/update/` é stub no-op. Não configurar webhook sem substituir o entrypoint.

### User Model & Auth
- **`AUTH_USER_MODEL = 'motoristas.Utilizador'`**. Sempre `get_user_model()` ou import de `motoristas.models`.
- **Custom auth backend**: `motoristas.backends.EmailBackend` (login por email, não username).
- **DRF sem `DEFAULT_PERMISSION_CLASSES`**. Views gerem auth individualmente.
- **`CorridaStatusView` é pública (sem auth)** — polling do passageiro. Não adicionar auth.
- **`IniciarCorridaView`** e **`CancelarCorridaMotoristaView`** usam `BotAuthMixin` e verificam ownership (`corrida.motorista == motorista`).

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
- **Painel operacional = `admin_mg/`** (custom), rota secreta via `ADMIN_SECRET_PATH`; login em `<PREFIX>/entrar/`. Em produção usar prefixo opaco.
- **`django.contrib.admin` também está montado em `/admin/`** (`settings.py:18`, `motogram/urls.py:8`). Não estender nem adicionar features ao admin do Django — o painel do produto é `admin_mg/`.

---

## Conventions

- **Linguagem**: comentários, strings, commits em PT-BR.
- **Models**: singular PascalCase (`Corrida`, não `Corridas`).
- **URLs**: kebab-case, plural para listas, singular para acções (`/api/corridas/{id}/aceitar/`).
- **Erros**: sempre `{'erro': 'mensagem legível'}` com HTTP status adequado. Nunca expor internals em 500s.
- **Lógica de negócio**: em `services.py`. Views só orquestram (validar → service → resposta).
- **Mensagens do bot**: constantes em `bot/messages.py`, nunca strings inline.
- **Estados FSM**: sempre `StatesGroup`, nunca strings soltas.
- **Templates**: mobile-first Tailwind CDN. Wrap em `<div class="max-w-md mx-auto min-h-dvh flex flex-col">` com `px-5`. Prefixo `sm:` para desktop.
- **Nunca retornar `telegram_id` ou tokens em respostas públicas.**

---

## Env Variables

Copiar `.env.example` para `.env`. Nuances:

- `BOT_SECRET` — token interno bot→backend. Gerar: `python -c "import secrets; print(secrets.token_hex(32))"`
- `PRECO_ASSINATURA_MENSAL=6900` — preço em centavos (R$ 69,00)
- `ADMIN_SECRET_PATH` — prefixo opaco da rota admin (default `admin_mg`)
- `DATABASE_URL` — Supabase PostgreSQL (com ou sem PostGIS conforme GDAL)
- `REDIS_URL` — Upstash Redis (opcional; sem ele usa LocMemCache + DB sessions)
- `BACKEND_URL` — usado pelo bot para chamar a API Django
- `SITE_URL` — URL pública do site
- `HERE_API_KEY` — chave HERE Maps para geocoding (backend only, 250k transações/mês grátis)
- `TWILIO_*` (opcional) — SMS para link de activação

Nunca commitar `.env`.

---

## Management Commands

```bash
python manage.py cancelar_corridas_antigas   # cancela corridas aguardando >10 min
python manage.py verificar_assinaturas        # desactiva motoristas com assinatura expirada
python manage.py notificar_vencimento         # alerta Telegram p/ assinaturas vencendo em 3 dias
```

---

## Design System

Paleta: primária `#1B7A3D` (verde), secundária `#C75B39` (terracotta), fundo `#FAF7F2`.
Tokens e padrões completos: `docs/DESIGN_SYSTEM.md`.
Protótipos: `docs/Identidade_Visual/` (HTML/CSS puro — traduzir para Tailwind CDN + Alpine.js).

---

## Docs Reference

| Doc | Quando ler |
|-----|-----------|
| `docs/ARCHITECTURE.md` | Modelos, endpoints, estrutura |
| `docs/HANDOFF.md` | Estado actual da sessão, bugs, prioridades |
| `docs/CONVENTIONS.md` | Naming, ordem de imports |
| `docs/TESTING.md` | Estratégia de testes, estrutura |
| `docs/CHECKLIST_TESTES_MANUAIS.md` | Checklist de testes manuais — fluxo completo do ciclo de vida |
| `docs/ROADMAP.md` | Backlog e fases |
| `docs/PASSENGER_APP.md` | Polling backoff, service worker |
| `docs/ONBOARDING.md` | Fluxos de registo |
| `docs/COMMUNICATION_FLOWS.md` | Fluxos site↔Telegram↔backend |
| `docs/DESIGN_SYSTEM.md` | Tokens, paleta, componentes |
