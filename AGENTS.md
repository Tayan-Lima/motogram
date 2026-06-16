# AGENTS.md — MotoGram

Plataforma de mototáxi para cidades pequenas no Brasil (interior do Amazonas).
Django 5 backend + aiogram 3 Telegram bot + Django Templates mobile-first site.

**Target users**: low-end Android, 3G with 500–2000ms latency, intermittent signal.

---

## Repo Structure

```
backend/          Django project (manage.py lives here)
  motogram/       Settings, urls, wsgi
  corridas/       Rides app (models, views, services, urls)
  motoristas/     Drivers + subscriptions app (also owns Utilizador model)
  pagamentos/     Mercado Pago Pix integration (webhook + services)
  site_publico/   Public site views (passenger, landing)
  admin_mg/       Admin panel views (NOT Django.contrib.admin)
  templates/      Django templates (passageiro/, motorista/, admin_mg/)
bot/              Standalone aiogram 3 process (separate from Django)
  main.py         Entry point (long-polling, MemoryStorage FSM)
  handlers/       FSM handlers (passageiro, motorista, corridas)
  services.py     HTTP calls to Django backend API
  states.py       aiogram FSM state definitions (StatesGroup classes)
  messages.py     All bot message strings (PT-BR constants)
backend/motoristas/bot_webhook.py  Telegram webhook stub (currently no-op, returns {"ok": True})
backend/static/sw.js              Service Worker for offline passenger page caching
docs/             All project docs (ARCHITECTURE.md, CONVENTIONS.md, etc.)
```

---

## Current State (as of 2026-06-12)

Phase 1 MVP is ~90% complete. Code is written but **migrations have not been generated** (no `migrations/` folder in any app) and **nothing is deployed yet**. See `docs/HANDOFF.md` for session state and next priorities. First tasks: generate/apply migrations, verify test coverage, deploy to Railway.

---

## Commands

```bash
# Install
pip install -r requirements.txt

# Django (from backend/)
python manage.py migrate
python manage.py runserver

# Bot (separate terminal, from bot/)
python main.py

# Tests (from backend/)
python manage.py test                        # all
python manage.py test motoristas             # single app
python manage.py test motoristas.tests.test_services.TokenTelegramTest  # single test class
python manage.py test --verbosity=2

# Coverage
coverage run manage.py test
coverage report --include="*/motoristas/*,*/corridas/*,*/pagamentos/*"
```

No linter, formatter, or typecheck commands are configured in this repo. No pre-commit hooks.

---

## Critical Architecture Rules

**Bot never touches the database.** Bot communicates with Django via HTTP (`bot/services.py` → Django API). Never `import` Django models in bot code. Auth is via `X-Bot-Secret` header, not `Authorization: Bearer`.

**Bot uses synchronous `requests`, not `aiohttp`.** This blocks the aiogram event loop during HTTP calls. This is a known tradeoff — keep `timeout=5` short to minimize blocking.

**Django sends Telegram notifications directly** via `requests.post` to `api.telegram.org`, not through the bot process. See `corridas/services.py`. Notifications are dispatched in background threads (`threading.Thread(daemon=True)`), never blocking the HTTP response.

**Two processes in production** — `Procfile` defines `web` (gunicorn, 2 workers) and `bot` (python main.py). Railway runs both.

**Custom user model** — `AUTH_USER_MODEL = 'motoristas.Utilizador'`. Always use `get_user_model()` or import from `motoristas.models`.

**Subscription gate on ride acceptance** — `AceitarCorridaView` checks `motorista.assinatura_activa` before allowing acceptance. Return 403 with `{'erro': '...'}`. Key properties: `motorista.assinatura_activa` (checks `activo`, `assinatura_ate`, and date validity) and `motorista.pode_receber_corridas` (also requires `status_cadastro == 'aprovado'` and `telegram_id`). Other driver endpoints (conclude, refuse) check ownership only, not subscription.

**PostGIS for driver location queries** — Motorista model uses `PointField(srid=4326)`. Use `ST_DWithin`, `Distance`, `D(km=...)`. Corrida model uses `FloatField` for lat/lon (not PostGIS) — this is intentional.

**`CorridaStatusView` is public (no auth)** — intentional, used by passengers for polling ride status. Do not add auth to this endpoint.

**No build step for frontend** — Tailwind CSS, Alpine.js, and Leaflet.js are loaded via CDN. Never introduce React, Vue, or any framework requiring a build pipeline.

**Leaflet.js loads lazy** — never in `<head>`. Only load when `abrirMapa()` is called. Passenger page HTML must be < 15KB.

---

## Conventions

- **Language**: code comments, user-facing strings, commit messages in PT-BR (Brazilian Portuguese)
- **Commit style**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- **Branches**: `main` (production, auto-deploys), `develop`, `feat/*`, `fix/*`
- **Model naming**: singular PascalCase (`Corrida`, not `Corridas`)
- **URL naming**: kebab-case, plural for lists, singular for actions (`/api/corridas/{id}/aceitar/`)
- **Error responses**: always `{'erro': 'human-readable message'}` with appropriate HTTP status. Never expose internal details in 500s.
- **Business logic**: goes in `services.py`, never in views. Views only orchestrate (validate → call service → return response).
- **Bot messages**: define as constants in `bot/messages.py`, never inline strings in handlers.
- **FSM states**: always in classes (`StatesGroup`), never loose strings.
- **Templates**: mobile-first with Tailwind CDN. Use `sm:` prefix for desktop breakpoints. Wrap content in `<div class="max-w-md mx-auto min-h-dvh flex flex-col">` with `px-5` padding on sections.

---

## Env Variables

Copy `.env.example` to `.env`. Key non-obvious ones:

- `BOT_SECRET` — internal token for bot→backend auth. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `PRECO_ASSINATURA_MENSAL=6900` — subscription price in centavos (R$ 69,00)
- `TELEGRAM_WEBHOOK_URL` — must be set to the public URL + `/api/bot/update/`
- `DATABASE_URL` — Supabase PostgreSQL with PostGIS enabled
- `SITE_URL` — public site URL (used in templates and links)

Never commit `.env`.

---

## Design System

Protótipos visuais em `docs/Identidade_Visual/` (HTML/CSS puro, sem Tailwind).
Tokens de design, paleta de cores e padrões de componentes em `docs/DESIGN_SYSTEM.md`.

- Seguir a paleta e tipografia do DESIGN_SYSTEM.md em todos os templates
- `motox-landing.html` é conceito alternativo (dark theme) — não é a identidade oficial
- Traduzir protótipos para Tailwind CDN + Alpine.js na implementação
- Cor primária: `#1B7A3D` (verde), secundária: `#C75B39` (terracotta), fundo: `#FAF7F2`

---

## Management Commands

```bash
python manage.py cancelar_corridas_antigas   # cancels rides waiting >10 minutes
python manage.py verificar_assinaturas        # deactivates drivers with expired subscriptions
python manage.py notificar_vencimento         # Telegram alerts for subscriptions expiring in 3 days
```

---

## Docs Reference

| Doc | When to read |
|-----|-------------|
| `docs/ARCHITECTURE.md` | Before creating models, endpoints, or changing project structure |
| `docs/CONVENTIONS.md` | Naming, code patterns, import order |
| `docs/TESTING.md` | Critical test cases and deploy checklist |
| `docs/ROADMAP.md` | Current phase and backlog |
| `docs/PASSENGER_APP.md` | Passenger site architecture, polling backoff, service worker, offline strategy |
| `docs/ONBOARDING.md` | Full driver/passenger registration flows and models |
| `docs/DESIGN_SYSTEM.md` | Design tokens, color palette, component patterns |
| `docs/COMMUNICATION_FLOWS.md` | All site↔Telegram↔backend communication flows |
| `docs/HANDOFF.md` | Session state, known bugs, next priorities |

---

## What Not To Do

- Don't use `Django.contrib.admin` for the user-facing admin panel — use views under `/admin_mg/`
- Don't use `FloatField` for GPS coordinates in new models — use `PointField` (PostGIS). Existing Corrida model uses FloatField (intentional legacy).
- Don't call Telegram API from Django views directly — use `corridas/services.py`
- Don't block passenger requests waiting for Telegram — timeout=5s, background thread
- Don't return `telegram_id` or tokens in public API responses
- Don't use Google Maps — always Leaflet.js + OpenStreetMap
- Don't poll with fixed intervals — use adaptive backoff (5s → 15s → 30s)
- Don't import Django models in bot code — bot talks to Django via HTTP only
- Don't use `aiohttp` in the bot — it currently uses sync `requests` (known tradeoff)

---

## Known Bugs (from HANDOFF.md)

- `BotAuthMixin` is duplicated in `corridas/views.py` and `motoristas/views.py` — should be consolidated
- `pagamentos/views.py` has inline business logic that should be in `services.py`
- `x-mask` Alpine plugin referenced in `motorista/cadastro.html` but never loaded in `base.html`
- `motoristas/proximos/` API endpoint leaks `telegram_id` in response — not intended for public consumption
