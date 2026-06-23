# HANDOFF.md — Motogram GO

**Última sessão**: 2026-06-23
**Estado**: Fase 1 (MVP) ~99% completa — **ciclo de vida completo**, deploy pendente
**Nota**: Sessão anterior crashou, mas código ficou íntegro. Venv precisou ser recriada.

---

## Estado Actual do Código

### ✅ Implementado (Fase 1)

| Componente | Estado | Ficheiros |
|-----------|--------|-----------|
| **Django project** | Configurado | `backend/motogram/settings.py`, `urls.py`, `wsgi.py` |
| **Models + migrations** | Gerados (4 apps) | `corridas/`, `motoristas/` (0004 email), `pagamentos/` (0002 mp_payment) |
| **PostGIS** | Funcional (detecção condicional) | `motoristas/models.py` PointField, `corridas/services.py` ST_DWithin |
| **Bot Telegram** | Long-polling, FSM, driver-only | `bot/main.py`, `bot/handlers/`, `bot/services.py` |
| **API Endpoints** | Todos criados e testados | `corridas/urls.py`, `motoristas/urls.py`, `pagamentos/urls.py` |
| **Services** | Limpos, sem lógica nas views | `corridas/services.py`, `motoristas/services.py`, `pagamentos/services.py` |
| **Site Passageiro** | Landing + pedido (mapa OSM) + cadastro + login + recuperar senha | `templates/passageiro/*.html` |
| **Site Motorista** | Cadastro (3 steps) + login + dashboard + conta + recuperar senha | `templates/motorista/*.html` |
| **Painel Admin** | Dashboard (MRR, gráfico 7d), KYC/CRM, assinaturas, rota secreta | `templates/admin_mg/*.html` (+ login) |
| **Pagamentos** | Mercado Pago Pix webhook (busca por `mp_payment_id`) | `pagamentos/services.py`, `pagamentos/views.py` |
| **Testes** | **114 testes**, 0 falhas | `backend/**/test*.py`, `backend/test_e2e.py`, `backend/playwright_tests/`, `bot/tests/` |
| **Mobile-first** | Tailwind CDN + Alpine.js + Leaflet.js (lazy) | `base.html` + templates |
| **Service Worker** | Escopo `/static/` corrigido, backoff adaptativo | `backend/static/sw.js` |
| **Management Commands** | 3 commands | `cancelar_corridas_antigas`, `verificar_assinaturas`, `notificar_vencimento` |
| **InDrive negotiation** | Oferta model, contra-oferta, escolher motorista | `corridas/models.py` Oferta, views, urls, services |
| **Ciclo de vida** | Iniciar, cancelar-motorista, notificar passageiro, distância Haversine | `corridas/views.py`, `services.py`, `bot/handlers/corridas.py` |
| **Bot novos handlers** | iniciar:, cancelar_motorista: + serviços HTTP | `bot/handlers/corridas.py`, `bot/services.py` |
| **Notificações passageiro** | Telegram ao iniciar/concluir/cancelar (thread separada) | `corridas/services.py` → `notificar_passageiro_telegram()` |
| **Distância automática** | Haversine ao concluir corrida (se não definida) | `corridas/services.py` → `calcular_distancia_km()` |
| **Bot security** | Token guardian — só motoristas ativados + assinatura ativa entram | `bot/handlers/start.py` |
| **Phone masking** | Mascarado antes do match (`****-8888`), real após match | `corridas/views.py` EscolherMotoristaView + CorridaStatusView |
| **Email confirmation** | Obrigatório p/ criar corrida; campos + migration + view + templates | `motoristas/views.py`, `site_publico/views.py`, `motoristas.0004_email_confirmado` |
| **Rate limiting** | django-ratelimit 5/min/IP nos 3 logins (passageiro, motorista, admin) | `site_publico/views.py`, `motoristas/views.py`, `admin_mg/views.py` |
| **URLs named** | Todas as URLs de templates convertidas para `{% url %}` (~100 ocorrências) | 24 templates |
| **PT-PT → PT-BR** | ~40 strings traduzidas (activo→ativo, registado→registrado, etc.) | 14 ficheiros |
| **Paleta consistente** | `gold/accent2/accent` em badges, erros, offline banner | 10+ templates |
| **GitHub** | Repo `Tayan-Lima/motogram` (público, main) | |

---

## Estatísticas de Testes (114 total)

| Suite | Testes | Runner |
|-------|--------|--------|
| Django unit + integration | 70 | `manage.py test` |
| Playwright E2E (passageiro) | 8 | `pytest playwright_tests/` |
| Playwright E2E (motorista) | 6 | `pytest playwright_tests/` |
| Playwright E2E (admin) | 4 | `pytest playwright_tests/` |
| Bot services (mock HTTP) | 11 | `pytest bot/tests/` |
| Bot handlers (start) | 5 | `pytest bot/tests/` |
| Bot handlers (motorista) | 6 | `pytest bot/tests/` |
| Bot handlers (corridas) | 4 | `pytest bot/tests/` |

### ⚠️ Pendente para Deploy

1. **Deploy Railway** — `Procfile` configurado mas não deployado
2. **Domínio** — não configurado
3. **LICENSE** — referenciada mas não criada (AGPL-3.0)
4. **MP webhook Sandbox** — lógica implementada e testada com unit tests, mas não com o Sandbox real do Mercado Pago

---

## Estado do Banco (dados de teste locais)

| Utilizador | Tipo | Motorista | Status | Localização |
|---|---|---|---|---|
| `admin` | admin | — | — | — |
| `marvio@gmail.com` (senha: `moto123`) | motorista | Márvio Silva | aprovado | Point(-60.0, -3.1) |
| `daniel@gmail.com` | motorista | Daniel Pereira | pendente | — |
| `teste1@gmail.com` | motorista | *(sem Motorista)* | quebrou | — |

- Token Telegram Márvio: link em `http://localhost:8000/motorista/conta/`
- Admin secret: `http://localhost:8000/g7x9kadm/entrar/` (admin / senha123)

---

## O que Mudou nesta Sessão (2026-06-23)

### Ciclo de Vida Completo das Corridas
- **Novos endpoints**: `POST /api/corridas/{id}/iniciar/` e `POST /api/corridas/{id}/cancelar-motorista/`
- **Novos handlers no bot**: `iniciar:`, `cancelar_motorista:` callbacks com FSM states
- **Novos métodos HTTP**: `bot/services.py` → `iniciar_corrida()`, `cancelar_corrida_motorista()`
- **Notificações ao passageiro**: `corridas/services.py` → `notificar_passageiro_telegram()` — disparado em thread separada ao iniciar, concluir, cancelar
- **Distância Haversine**: `calcular_distancia_km()` em `corridas/services.py` — calculada automaticamente ao concluir se não definida
- **Cron job atualizado**: `cancelar_corridas_antigas` agora lida com estado `cancelada` → `sem_motoristas`
- **Botões dinâmicos**: Telegram mostra [🏍️ Iniciar] + [❌ Cancelar] após match, depois só [✅ Concluir]

### Fluxo de estados
```
aguardando ──▶ aceite ──▶ em_curso ──▶ concluida
                 │                      │
                 └──▶ cancelada ◀───────┘
                      (motorista)
```

### Estatísticas de Testes (70 Django confirmados)
| Suite | Testes | Status |
|-------|--------|--------|
| Django unit + integration | 70 | ✅ OK (0 falhas) |
| Playwright E2E | 18 | ⚠️ Não executado nesta sessão (precisa de navegador) |
| Bot tests | 26 | ⚠️ Não executado nesta sessão (precisa de venv separada) |
| **Total** | **114** | |

### Incidente da Sessão
- Crash no final da sessão anterior; venv ficou limpa
- Dependências reinstaladas via `pip install -r requirements.txt`
- Código-fonte 100% íntegro (git confirma)
- 2 conexões zumbis no PostgreSQL limpadas com `--keepdb`

### Checklist de Testes Manuais
Ver `docs/CHECKLIST_TESTES_MANUAIS.md` — cobre 4 fluxos + edge cases + regressão.

---

## Env Variables Essenciais

```bash
DATABASE_URL=postgresql://motogram:motogram_dev@localhost:5432/motogram  # local
TELEGRAM_TOKEN=<TELEGRAM_TOKEN>
BOT_SECRET=dev-secret-token-change-in-production
SITE_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
MP_ACCESS_TOKEN=...
MP_WEBHOOK_SECRET=...
PRECO_ASSINATURA_MENSAL=6900
ADMIN_SECRET_PATH=g7x9kadm
EMAIL_HOST=...
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

---

## Como Rodar

```bash
# Terminal 1 — Django
cd backend && source /home/gamer/Área/bin/activate
python manage.py runserver 0.0.0.0:8000

# Terminal 2 — Bot Telegram
cd bot && source .venv/bin/activate
python main.py

# Testes
cd backend && source /home/gamer/Área/bin/activate && python manage.py test --verbosity=2
cd backend && python -m pytest playwright_tests/ -v
cd bot && .venv/bin/python -m pytest tests/ -v
```

**Dois ambientes Python distintos:**
- Django: `/home/gamer/Área/` — Python 3.14
- Bot: `bot/.venv/` via uv — Python 3.12, aiogram 3

---

## Próximos Passos (ordem de prioridade)

1. **Testar fluxo completo** — seguir `docs/CHECKLIST_TESTES_MANUAIS.md` no browser + Telegram
2. **Deploy Railway** — criar conta, linkar GitHub, configurar env vars
3. **Criar admin superuser** no Railway: `python manage.py createsuperuser` com `tipo='admin'`
4. **Teste real** — celular Android em 4G/3G: motorista no Telegram, passageiro no Chrome
5. **LICENSE** — discutir e criar (AGPL-3.0)
6. **MP webhook Sandbox** — testar com Sandbox real do Mercado Pago

## Próximas Features (Fase 2 — backlog)

- Dashboard avançado motorista (ganhos, metas, combustível)
- WebSocket (Django Channels) substituindo polling REST
- Avaliação 1–5 estrelas pós-corrida
- SMS notificação (Zenvia)
- Sentry monitoramento de erros
- Dark mode (Tailwind + Alpine.js toggle)
