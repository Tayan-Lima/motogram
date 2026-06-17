# HANDOFF.md — MotoGram

**Última sessão**: 2026-06-17
**Estado**: Fase 1 (MVP) ~95% completa — 62 testes passando, deploy pendente

---

## Estado Actual do Código

### ✅ Implementado (Fase 1 — Semanas 1–6)

| Componente | Estado | Ficheiros |
|-----------|--------|-----------|
| **Django project** | Configurado | `backend/motogram/settings.py`, `urls.py`, `wsgi.py` |
| **Models + migrations** | Gerados e aplicados | `corridas/`, `motoristas/`, `pagamentos/` (migrations 0001–0003) |
| **PostGIS** | Funcional local (PostgreSQL) | `motoristas/models.py` PointField, `corridas/services.py` ST_DWithin |
| **Bot Telegram** | Driver-only, funcional | `bot/main.py`, `bot/handlers/`, `bot/services.py`, `bot/messages.py` |
| **API Endpoints** | Todos criados e testados | `corridas/urls.py`, `motoristas/urls.py`, `pagamentos/urls.py` |
| **Services** | Criados e limpos | `corridas/services.py` (enviar_localizacao_telegram, notificar_motoristas_proximos), `motoristas/services.py` |
| **Site Passageiro** | Landing + pedido + cadastro + login + recuperar senha | `templates/passageiro/*.html` |
| **Site Motorista** | Cadastro, login, dashboard, conta + recuperar senha | `templates/motorista/*.html` |
| **Painel Admin** | Dashboard, cadastros, corridas, motoristas — rota secreta | `templates/admin_mg/*.html` (+ `login.html`) |
| **Pagamentos** | Mercado Pago Pix webhook (lógica em services.py) | `pagamentos/services.py`, `pagamentos/views.py` |
| **Testes** | **62 testes** em 9 ficheiros, 0 falhas | `backend/**/test*.py` |
| **Service Worker** | Criado | `backend/static/sw.js` |
| **Management Commands** | 3 commands | `cancelar_corridas_antigas`, `verificar_assinaturas`, `notificar_vencimento` |
| **InDrive negotiation** | Oferta model, contra-oferta, escolher motorista | `corridas/models.py` Oferta, views, urls, services |
| **Bot security** | Token guardian — só motoristas ativados entram | `bot/handlers/start.py` |
| **Phone masking** | `****-8888` em todas as saídas | `corridas/views.py` _mascarar_telefone |
| **Localização no Telegram** | Pin no mapa via sendLocation | `corridas/services.py` enviar_localizacao_telegram |
| **Senha nos cadastros** | Motorista (step 1) e passageiro (step 2) pedem senha | templates + views |
| **Recuperar senha** | Ambos via e-mail → Telegram | `motorista/recuperar-senha/`, `passageiro/recuperar-senha/` |
| **GitHub** | Repo `Tayan-Lima/motogram` (público, main) | |

### ⚠️ Pendente

1. **Deploy Railway** — `Procfile` configurado mas não deployado
2. **Domínio** — não configurado
3. **URLs hardcoded** nos templates (usar `{% url %}` com namespaces)
4. **Rate limiting** nas views de login (produção)
5. **LICENSE** — referenciada mas não criada

---

## Estado do Banco (dados de teste locais)

| Utilizador | Tipo | Motorista | Status | Localização |
|---|---|---|---|---|
| `admin` | admin | — | — | — |
| `marvio@gmail.com` (senha: `moto123`) | motorista | Márvio Silva | aprovado | Point(-60.0, -3.1) |
| `daniel@gmail.com` | motorista | Daniel Pereira | pendente | — |
| `teste1@gmail.com` | motorista | *(sem Motorista)* | quebrou | — |

- Token Telegram Márvio: usar o link no site `http://localhost:8000/motorista/conta/`
- Admin secret: `http://localhost:8000/g7x9kadm/entrar/` (admin / senha123)

---

## O que Mudou nesta Sessão (2026-06-17)

### Correções
- **`BotAuthMixin` unificado** — `corridas/views.py` e `motoristas/views.py` importam de `motogram/mixins.py`
- **Webhook movido para services** — `verificar_assinatura_webhook()` + `processar_webhook_mercadopago()` em `pagamentos/services.py`
- **PostGIS detection fix** — `settings.py` usa `ctypes.util.find_library('gdal')` em vez de import prematuro
- **Admin voltar hardcoded** — `cadastros_pendentes.html` usava `/admin_mg/` em vez de `{{ prefix }}`
- **Bot decode_payload removido** — `bot/handlers/start.py` usa `command.args` directamente
- **Link do site aponta pra bot errado** — `motoristas/views.py` link corrigido de `motogram_bot` para `MotoGram_Go_bot`
- **Cadastro quebrava com campos vazios** — validação completa de campos obrigatórios antes de `int()`/`float()`

### Features novas
- **Pin no mapa no Telegram** — `enviar_localizacao_telegram()` envia `sendLocation` com origem e destino
- **Senha nos cadastros** — motorista (step 1) e passageiro (step 2) agora pedem senha (mín. 6 caracteres)
- **Recuperar senha** — ambos: digita e-mail → nova senha enviada via Telegram
- **Links "Esqueceu a senha?"** nas páginas de login

### Testes
- 62 testes (eram 41 no HANDOFF anterior), 0 falhas
- Testes de cadastro actualizados para incluir `password`/`password_confirm` nos POSTs

---

## Próximos Passos (ordem de prioridade)

1. **Deploy Railway** — criar conta, linkar GitHub, configurar env vars (DATABASE_URL no Supabase, etc.)
2. **Criar admin superuser** no Railway: `python manage.py createsuperuser` com `tipo='admin'`
3. **Teste real** — com celular em 3G: motorista no Telegram, passageiro no navegador
4. **Converter URLs hardcoded** nos templates para `{% url %}` com namespaces
5. **Rate limiting** nas views de login
6. **Criar LICENSE** (AGPL-3.0)
7. **Testes para bot/** (0 testes actualmente) e **admin_mg/**
8. **Tratar destino no frontend** — `pedir.html` bug: `destino_lat` copia `origem_lat`

---

## Env Variables Essenciais

```bash
DATABASE_URL=postgresql://motogram:motogram_dev@localhost:5432/motogram  # local
TELEGRAM_TOKEN=<TELEGRAM_TOKEN>
BOT_SECRET=dev-secret-token-change-in-production
SITE_URL=http://localhost:8000
MP_ACCESS_TOKEN=...
MP_WEBHOOK_SECRET=...
PRECO_ASSINATURA_MENSAL=6900
ADMIN_SECRET_PATH=g7x9kadm
```

**Para produção (Railway):** `DATABASE_URL` do Supabase, `SITE_URL` do Railway, `SECRET_KEY` e `BOT_SECRET` novos, `DEBUG=False`, `ALLOWED_HOSTS` com domínio Railway.

---

## Como Rodar

```bash
# Terminal 1 — Django
cd backend && source ../venv/bin/activate
python manage.py runserver 0.0.0.0:8000

# Terminal 2 — Bot Telegram
cd bot && source .venv/bin/activate
python main.py

# Testes
cd backend && python manage.py test --verbosity=2
```

**Bot roda com Python 3.12 via uv** (`bot/.venv`), separado do venv do Django (Python 3.14). O bot usa long-polling (não webhook).

---

## Bugs Conhecidos

1. **Destino copia origem** — `pedir.html:249-250` `destino_lat = this.lat` (deveria capturar coordenada separada)
2. **Bot usa `requests` síncrono** — bloqueia event loop do aiogram (timeout=5s, conhecido e aceito)
3. **`x-mask` Alpine plugin** — referenciado em `cadastro.html` mas não carregado no `base.html`
4. **`motoristas/proximos/`** — endpoint vaza `telegram_id` (não deveria ser público)

---

## Próximas Features (Fase 2)

- Dashboard avançado do motorista (ganhos, metas, combustível)
- WebSocket (Django Channels) substituindo polling
- Sistema de avaliação (1–5 estrelas)
- SMS de notificação (Zenvia)
- Sentry para monitoramento de erros
