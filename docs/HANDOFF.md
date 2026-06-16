# HANDOFF.md — MotoGram

**Última sessão**: 2026-06-12
**Estado**: Fase 1 (MVP) ~90% completa

---

## Estado Actual do Código

### ✅ Implementado (Fase 1 — Semanas 1–5)

| Componente | Estado | Ficheiros |
|-----------|--------|-----------|
| **Django project** | Configurado | `backend/motogram/settings.py`, `urls.py`, `wsgi.py` |
| **Models** | Todos criados | `corridas/models.py`, `motoristas/models.py`, `pagamentos/models.py` |
| **Bot Telegram** | Funcional | `bot/main.py`, `bot/handlers/`, `bot/services.py`, `bot/messages.py` |
| **API Endpoints** | Todos criados | `corridas/urls.py`, `motoristas/urls.py`, `pagamentos/urls.py` |
| **Services** | Criados | `corridas/services.py`, `motoristas/services.py` |
| **Site Passageiro** | Landing + pedido | `templates/passageiro/pedir.html`, `templates/site_publico/landing.html` |
| **Site Motorista** | Cadastro, login, dashboard, conta | `templates/motorista/*.html` (6 templates) |
| **Painel Admin** | Dashboard, cadastros, corridas, motoristas | `templates/admin_mg/*.html` (4 templates) |
| **Pagamentos** | Mercado Pago Pix webhook | `pagamentos/views.py` |
| **Testes** | 41 testes em 8 ficheiros | `backend/**/test*.py` |
| **Service Worker** | Criado | `backend/static/sw.js` |
| **Management Commands** | 3 commands | `cancelar_corridas_antigas`, `verificar_assinaturas`, `notificar_vencimento` |

### ⚠️ Pendente (Fase 1 — Semana 6)

1. **Migrations não geradas** — pasta `migrations/` não existe em nenhum app
2. **Deploy Railway** — `Procfile` configurado mas não deployado
3. **Domínio** — não configurado
4. **Testes e2e** — `test_e2e.py` existe mas Django não está instalado no ambiente actual

---

## O que Fazer na Próxima Sessão

### Prioridade 1: Gerar e aplicar migrations

```bash
cd backend
pip install -r requirements.txt  # instalar dependências primeiro
python manage.py makemigrations
python manage.py migrate
python manage.py test --verbosity=2  # verificar que tudo funciona
```

### Prioridade 2: Verificar cobertura de testes

- Ler `docs/TESTING.md` para ver os testes críticos obrigatórios
- Verificar se todos os 41 testes passam
- Identificar gaps (especialmente: webhook Mercado Pago, matching geográfico, token Telegram)

### Prioridade 3: Deploy (se utilizador quiser)

- Configurar `.env` com credenciais reais
- Railway: `railway login && railway up`
- Verificar `Procfile`: `web: cd backend && gunicorn motogram.wsgi:application --bind 0.0.0.0:$PORT --workers 2`

---

## Arquitectura Resumida

```
SITE PASSAGEIRO          DJANGO BACKEND            TELEGRAM MOTORISTA
(Chrome/3G)              (Railway/Python)           (App Telegram)
     │                        │                         │
     │ POST /passageiro/      │                         │
     │ pedir/                 │                         │
     │───────────────────────►│                         │
     │                        │ POST api.telegram.org   │
     │                        │ sendMessage (background)│
     │                        │────────────────────────►│
     │                        │                         │
     │ GET /api/corridas/     │                         │
     │ {id}/status/ (polling) │◄────────────────────────│
     │◄───────────────────────│ POST /api/corridas/     │
     │                        │ {id}/aceitar/ (bot)     │
     │                        │◄────────────────────────│
```

**Regra de ouro**: Bot nunca toca na base de dados. Bot comunica com Django via HTTP (`X-Bot-Secret` header).

---

## Ficheiros Críticos para Ler

| Ficheiro | Porquê |
|----------|--------|
| `AGENTS.md` (root) | Regras para agentes — ler antes de qualquer mudança |
| `docs/ARCHITECTURE.md` | Modelos, endpoints, fluxos de comunicação |
| `docs/CONVENTIONS.md` | Naming, padrões de código |
| `docs/TESTING.md` | Testes críticos e checklist de deploy |
| `docs/ROADMAP.md` | Próximas features (Fase 2: dashboard avançado, WebSocket) |
| `docs/PASSENGER_APP.md` | Arquitectura do site do passageiro (polling, service worker) |

---

## Bugs / Observações Notadas

1. **`BotAuthMixin` duplicado** — existe em `corridas/views.py` e `motoristas/views.py`. Pode ser extraído para um módulo partilhado.
2. **`pagamentos/views.py` tem lógica de negócio inline** — `_criar_pix_mp()` deveria estar em `pagamentos/services.py` (não existe).
3. **Bot usa `requests` síncrono** — bloqueia o event loop do aiogram durante chamadas HTTP. Conhecido, manter `timeout=5`.
4. **Testes referenciam `motoristas.tests.test_services.TokenTelegramTest`** — verificar se este ficheiro de teste existe (não foi encontrado no glob).

---

## Env Variables Essenciais

```bash
DATABASE_URL=postgresql://...     # Supabase PostgreSQL com PostGIS
REDIS_URL=redis://...             # Upstash Redis
TELEGRAM_TOKEN=...               # Bot Telegram
BOT_SECRET=...                   # Token interno bot→backend (gera com secrets.token_hex(32))
MP_ACCESS_TOKEN=...              # Mercado Pago
MP_WEBHOOK_SECRET=...            # Mercado Pago webhook validation
SITE_URL=https://motogram.app    # Usado em templates e links
PRECO_ASSINATURA_MENSAL=6900     # R$ 69,00 em centavos
```

---

## Próximas Features (Fase 2)

- Dashboard avançado do motorista (ganhos por período, metas, combustível)
- WebSocket (Django Channels) substituindo polling
- Sistema de avaliação (1–5 estrelas)
- SMS de notificação de vencimento (Twilio/Zenvia)
- Sentry para monitoramento de erros
