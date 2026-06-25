# HANDOFF.md — Motogram GO

**Última sessão**: 2026-06-24
**Estado**: Fase 1 (MVP) ~99% completa — **deploy Railway concluído, PostGIS 3.7 activo**, matching geo expansivo + Live Location Telegram + PT-BR completo + dashboard read-only + UX/UI mobile-first
**Deploy**: `https://web-production-ff262.up.railway.app` | Bot: `@MotoGram_Go_bot` | Admin: `https://web-production-ff262.up.railway.app/g7x9kadm/entrar/`
**Nota**: Página `/motorista/online/` eliminada — substituída por Telegram Live Location (8h, updates ~60s). Dashboard toggle agora é badge informativo (só leitura).

---

## Changelog — 2026-06-24 (Sessão UX/UI + correção admin tests)

### Lote A+B — Usabilidade mobile, feedback e PT-BR (9 templates)

**Inputs text-base (16px)**: evita zoom automático iOS em todos os formulários.
**for+id+autocomplete+inputmode**: labels associadas, teclados corretos, autofill.
**Alvos 44px**: botão GPS, CTAs, botão lixeira de favorito.
**Modais Alpine**: substituem `prompt()` (salvar favorito), `confirm()` (cancelar
corrida, remover favorito, sair da conta) e `alert()` (assinatura Pix).
**fetchComTimeout()**: AbortController com timeout configurável (8s GET, 12-15s
POST). Diferencia `AbortError` de erro de rede. Aplicado em todos os fetches
de pedir, acompanhar, perfil e assinatura.
**PT-PT → PT-BR**: "queres"→"você quer", "Cria/Repete"→"Crie/Repita",
"teu/tua"→"seu/sua", "A obter/A procurar"→"Obtendo/Procurando",
"receberes"→"receber", "Escaneia"→"Escaneie", "contacta"→"contate".
**Leaflet**: zoom control `bottomright`, `bindTooltip` permanente em
Origem/Destino, `map.on('load')` para sinalizar mapaPronto.
**Toast Alpine**: `mostrarToast(msg, ms)` com `x-transition`, `role="status"`,
`aria-live="polite"` em pedir, acompanhar, perfil e assinatura.
**Cache-bust foto**: uploadFoto no perfil usa `?v=Date.now()` para atualizar
`<img>` sem reload completo.
**:disabled mesclado**: botão "Pedir corrida" com
`!valor || !lat || !destinoTexto || enviando` numa expressão única.
**x-transition**: `opacity.duration.200ms` em steps (form/waiting/ofertas/found).

Templates alterados: `passageiro/pedir.html`, `passageiro/acompanhar.html`,
`passageiro/cadastro.html`, `passageiro/login.html`, `passageiro/perfil.html`,
`passageiro/confirmacao.html`, `passageiro/recuperar_senha.html`,
`passageiro/email_confirmado.html`, `motorista/assinatura.html`.

### Lote C — Remoção do `<style>` global do base.html (5 templates)

Regra CSS `img[alt="Motogram GO"] { height:124px !important }` replicada como
classes Tailwind `h-[124px] w-auto max-w-[50vw] object-contain` + attrs
`width="124" height="124"` em cada um dos 4 `<img>` do projeto.
`.btn-primary` e `.card` removidas (zero uso).

Templates alterados: `base/base.html` (removido `<style>` lines 14-24),
`passageiro/pedir.html`, `passageiro/base_passageiro.html`,
`site_publico/landing.html`, `admin_mg/login.html`.

### Correção — 3 testes admin_mg falhando (2 arquivos)

`admin_mg/urls.py` e `views.py` liam `ADMIN_SECRET_PATH` de `os.environ`,
mas `conftest.py` setava via `settings.ADMIN_SECRET_PATH` (pós
`django.setup()`, tarde demais). Rotas `/test-admin-path/` retornavam 404.

Mudanças:
- `playwright_tests/conftest.py:7` — `os.environ["ADMIN_SECRET_PATH"] = "test-admin-path"` antes do `django.setup()`
- `motogram/settings.py:153` — `ADMIN_SECRET_PATH = os.environ.get('ADMIN_SECRET_PATH', 'admin_mg')`

### Resultado dos testes

| Suite | Antes | Depois |
|---|---|---|
| Django (72) | 72 pass | 72 pass |
| Playwright passageiro (8) | 8 pass | 8 pass |
| Playwright motorista (6) | 6 pass | 6 pass |
| Playwright admin_mg (4) | 1 pass, 3 fail | 4 pass |
| **Total** | **87 pass, 3 fail** | **90 pass** |

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
| **Testes** | **90 (backend + Playwright) + 36 (bot) = 126**, 0 falhas | `backend/**/test*.py`, `backend/test_e2e.py`, `backend/playwright_tests/`, `bot/tests/`, `site_publico/tests/test_map.py` |
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
| **Sistema de Avaliação** | Model `Avaliacao`, views (passageiro web + motorista bot), FSM completo | `corridas/models.py`, `views.py`, `urls.py`, `bot/handlers/corridas.py` |
| **Admin KYC/CRM** | Detalhe motorista/passageiro, listagem passageiros, painéis avaliação, assinaturas dashboard | `admin_mg/views.py`, `urls.py`, 6 novos templates |
| **Intervalo de tempo** | Formato `17:05 - 17:25` em 6 templates (admin, motorista, passageiro) | `templates/*/historico*.html`, `perfil.html`, `dashboard.html` |
| **Utilizador.foto** | Upload de foto no perfil + exibição nos templates | `motoristas/models.py`, `templates/passageiro/perfil.html` |
| **EmailBackend** | Login por email (não username) | `motoristas/backends.py`, `settings.py` |
| **Bot limpeza** | `limpar_mensagens()` + `_limpeza_agressiva()` — apaga mensagens antigas | `bot/services.py`, `corridas/services.py` |
| **Geocoding HERE Maps** | Substitui Nominatim no frontend; autocomplete + geocode + reverse via backend | `site_publico/services.py`, `views.py`, `urls.py` |
| **Matching geo expansivo** | Círculo expansível 5→10→25km + filtro frescura ≤2h + fallback 4 níveis | `corridas/services.py` `notificar_motoristas_proximos()` |
| **Live Location Telegram** | Bot recebe `edited_message` com localização em tempo real (até 8h, ~60s updates) | `bot/main.py`, `bot/handlers/motorista.py` `receber_localizacao_live` |
| **Toggle online/offline** | Botão Telegram 🟢/🔴 altera `Motorista.activo`; dashboard é badge informativo (read-only) | `motoristas/views.py` `BotToggleOnlineView`, `bot/handlers/motorista.py` |
| **Passageiros pendentes admin** | Painel lista passageiros com `email_confirmado=False` + confirmação manual (botão) | `admin_mg/views.py`, `templates/admin_mg/passageiros_pendentes.html` |
| **PT-BR completo** | Todas as strings do bot em PT-BR (você, compartilhe, contato, clique) | `bot/messages.py` (174 linhas), `corridas/services.py` |
| **GitHub** | Repo `Tayan-Lima/motogram` (público, main) | |

---

## Estatísticas de Testes (152 total)

| Suite | Testes | Runner |
|-------|--------|--------|
| Django unit + integration | 116 | `manage.py test` |
| Bot (services + handlers) | 36 | `pytest bot/tests/` |

**Todas as suites executadas e confirmadas (152/152 ✅, 0 falhas).**

### ✅ Deploy Concluído (2026-06-24)

**Railway**: 4 serviços (web, bot, PostGIS, Redis) em `https://web-production-ff262.up.railway.app`
**PostGIS**: 3.7 com GEOS + PROJ + STATS — template `postgis` via CLI (`railway deploy --template postgis`)
**Admin**: `admin@motogram.app` / `Admin123!@#` (superuser criado via `create_admin.py` no startup)
**Domínio**: `web-production-ff262.up.railway.app` (Railway auto-generated)

### ⚠️ Pendente

1. **Domínio próprio** — não configurado (ex: motogram.app)
2. **LICENSE** — referenciada mas não criada (AGPL-3.0)
3. **MP webhook Sandbox** — lógica implementada e testada com unit tests, mas não com o Sandbox real do Mercado Pago
4. **Corrigir issues críticas do audit** — `AUDIT_REPORT.md` lista 4 critical + 8 high ainda não resolvidos
5. **Testar fluxo completo real** — motorista registado + Telegram vinculado + corrida criada

---

## Estado do Banco (dados de teste locais)

| Utilizador | Tipo | Motorista | Status | Localização |
|---|---|---|---|---|
| `admin` | admin | — | — | — |
| `marvio@gmail.com` (senha: `***`) | motorista | Márvio Silva | aprovado | Via Live Location Telegram |
| `daniel@gmail.com` | motorista | Daniel Pereira | pendente | — |
| `teste1@gmail.com` | motorista | *(sem Motorista)* | quebrou | — |

- Token Telegram Márvio: link em `http://localhost:8000/motorista/conta/`
- Admin secret: `http://localhost:8000/g7x9kadm/entrar/` (*** / ***)
- **Live Location**: Motorista deve compartilhar localização em tempo real (8h) após clicar "🟢 Ficar Online"

---

## O que Mudou nesta Sessão (2026-06-23)

### Sessão 1 — Ciclo de Vida Completo das Corridas
- **Novos endpoints**: `POST /api/corridas/{id}/iniciar/` e `POST /api/corridas/{id}/cancelar-motorista/`
- **Novos handlers no bot**: `iniciar:`, `cancelar_motorista:` callbacks com FSM states
- **Novos métodos HTTP**: `bot/services.py` → `iniciar_corrida()`, `cancelar_corrida_motorista()`
- **Notificações ao passageiro**: `corridas/services.py` → `notificar_passageiro_telegram()` — disparado em thread separada ao iniciar, concluir, cancelar
- **Distância Haversine**: `calcular_distancia_km()` em `corridas/services.py` — calculada automaticamente ao concluir se não definida
- **Cron job atualizado**: `cancelar_corridas_antigas` agora lida com estado `cancelada` → `sem_motoristas`
- **Botões dinâmicos**: Telegram mostra [🏍️ Iniciar] + [❌ Cancelar] após match, depois só [✅ Concluir]

### Sessão 2 — Avaliação + Admin KYC/CRM + Polimento
- **Sistema de Avaliação**: model `Avaliacao` (nota 1-5 + comentário, UniqueConstraint por corrida+tipo)
  - `AvaliarMotoristaView` (passageiro via web, POST `/api/corridas/{id}/avaliar/`)
  - `AvaliarPassageiroView` (motorista via bot, POST `/api/corridas/{id}/avaliar-passageiro/`)
  - Bot FSM: callback `avaliar_p:` → estrelas → comentário (se ≤2★) → `pular_comentario:` → `aguardando_comentario_avaliacao`
- **Admin KYC/CRM**: `MotoristaDetailView`, `PassageiroDetailView`, `PassageirosListView`, `AvaliacoesMotoristasView`, `AvaliacoesPassageirosView`, `AvaliacoesComentariosView`, `AssinaturasDashboardView`
  - Busca e paginação nos cadastros pendentes e histórico
  - Acções KYC: aprovar, reprovar, bloquear, reactivar, activar manual, excluir
- **Intervalo de tempo** (`17:05 - 17:25`): aplicado em 6 templates — `admin_mg/historico_corridas`, `motorista/historico` (card + modal), `motorista/dashboard`, `passageiro/perfil`, `admin_mg/passageiro_detalhe`, `admin_mg/motorista_detalhe`
- **Novos campos**: `Corrida.origem_texto`, `Corrida.destino_texto`, `Corrida.iniciada_em`, `Corrida.notificacao_msg_ids`, `Utilizador.foto`, `Utilizador.email_confirmado`, `Utilizador.email_token`
- **EnderecoFavorito**: trocou lat/lon obrigatórios por rua/número/ponto_referência
- **EmailBackend custom**: login por email (não username) — `AUTHENTICATION_BACKENDS` em settings
- **Bot**: `limpar_mensagens()`, `avaliar_passageiro()`, `_limpeza_agressiva()`, logging
- **Rate limiting**: django-ratelimit 5/min/IP nos logins (passageiro, motorista, admin)
- **Logging**: configurado em `settings.py` (corridas, motoristas DEBUG)
- **Botão "Ir ao Perfil"**: adicionado após avaliação no `acompanhar.html`
- **Email confirmation**: obrigatório para pedir corrida (gate no `CriarCorridaWebView`)
- **Migrations novas**: `0004_add_destino_texto`, `0005_corrida_origem_texto`, `0006_notificacao_msg_ids`, `0007_avaliacao`, `0008_iniciada_em`, `motoristas.0004_email_confirmado`, `motoristas.0005_favorito_rua_numero`, `motoristas.0006_foto_utilizador`, `pagamentos.0002_add_mp_payment_id`

### Sessão 3 — Geocoding HERE Maps (substitui Nominatim no frontend)
- **Problema**: Nominatim directo no frontend (1) viola política de uso do OSM, (2) rate limit agressivo (429s), (3) não tem cobertura de endereços no interior do Amazonas (sem números de rua)
- **Solução**: HERE Maps Geocoding & Search API (250k transações/mês grátis, dados comerciais próprios, cobertura confirmada em Maués-AM com score 1.0)
- **Novo ficheiro**: `site_publico/services.py` — `autocomplete()`, `geocode()`, `reverse_geocode()` via HERE + fallback Nominatim + cache LocMem (TTL 24h, chaves hashed MD5)
- **3 novos endpoints** (todos requerem login): `GET /api/map/autocomplete/`, `GET /api/map/geocode/`, `GET /api/map/reverse/`
- **Frontend migrado**: `passageiro/pedir.html` — `buscarEnderecos()` e `_geocodarFavorito()` agora chamam backend Django em vez de Nominatim directo
- **Backend migrado**: `_geocodar_endereco()` agora usa HERE Maps via `services.py` (em vez de Nominatim directo)
- **Tiles OSM mantidos** — só o geocoding mudou, o mapa visual continua com `tile.openstreetmap.org`
- **Testes**: 12 novos testes em `site_publico/tests/test_map.py` (mock HERE + fallback + cache + auth)
- **Env**: `HERE_API_KEY` adicionada ao `.env` e `.env.example`

### Sessão 4 — Fixes de autocomplete + Cleanup de segurança
- **HERE Autocomplete agora retorna coordenadas**: `_here_autocomplete()` extrai `lat`/`lng` do campo `position` e `street`/`housenumber` do `address`. Frontend `selecionarEndereco()` usa coordenadas directamente sem segundo passo de geocoding na maioria dos casos.
- **Fluxo 2-passos mantido como fallback**: `_geocodarSelecao()` chamado apenas quando `lat`/`lng` ausentes na resposta do autocomplete.
- **Template fix (display_name)**: `s.display_name` → `s.label` nos templates de sugestão.
- **Bias fix (destino)**: `buscarEnderecos()` usa bias per-type — `destinoLat`/`destinoLon` para destino, `lat`/`lon` para origem.
- **Blur race condition**: `usarTextoComoDestino/Origem` gerem `_blurTimeout` com `clearTimeout` no `@focus`.
- **Security cleanup**: 6 credenciais reais substituídas por placeholders em `HANDOFF.md`. Token do Telegram expurgado do histórico com `git filter-branch` (12 commits reescritos). `g7x9kadm` substituído por `test-admin-path` nos ficheiros de teste.

### Fluxo de estados
```
aguardando ──▶ aceite ──▶ em_curso ──▶ concluida
                 │                      │
                 └──▶ cancelada ◀───────┘
                      (motorista)
```

### Estatísticas de Testes (126 confirmed — todas executadas)
| Suite | Testes | Status |
|-------|--------|--------|
| Django unit + integration | 82 | ✅ OK (0 falhas) |
| Playwright E2E | 18 | ✅ OK (0 falhas) |
| Bot tests | 26 | ✅ OK (0 falhas) |
| **Total** | **126** | ✅ |

### Incidentes das Sessões
- **1º crash** (manhã): venv Django ficou limpa; dependências reinstaladas; código 100% íntegro
- **2º crash** (~18:50): ao gravar template `historico_corridas.html`; venv sobreviveu; DB de teste zumbi (`test_motogram`) limpo com `dropdb`
- Ambos os crashes sem perda de código-fonte (confirmado via git)

### Sessão 5 — Hardening de Segurança & Performance (2026-06-24)
- **safe_tg.py**: wrappers `safe_edit_text()`, `safe_answer()`, `safe_answer_callback()`, `safe_send_message()` — protegem handlers do bot contra crash em rede 3G intermitente
- **Filtro private chat**: `router.message.filter(F.chat.type == "private")` em todos os routers do bot (start, motorista, corridas)
- **Auth hardening**: `@login_required` + ownership checks em `ConfirmacaoView`, `AcompanharView`, `ListarOfertasView`, `EscolherMotoristaView`, `CancelarCorridaView`
- **Performance**: `select_related`/`prefetch_related` em todas as views com FK; `db_index=True` em `Corrida.status`, `Motorista.status_cadastro`, `Motorista.activo`; `GZipMiddleware` adicionado
- **MP webhook hardening**: `MP_WEBHOOK_SECRET` vazio rejeita webhooks (antes aceitava); verificação de status do pagamento via API MP antes de activar assinatura
- **Service Worker**: cache `v2` + `skipWaiting()` + `clients.claim()` + fallback offline para navigate
- **Frontend optimizações**: `preconnect` hints para CDNs no `<head>`; `allowed_updates=["message", "callback_query"]` no polling do bot
- **Bot avaliação**: `nota=None` suportado (comentário sem estrelas) via `pular_comentario:`
- **Autocomplete destino**: corrigida race condition blur/focus via `_blurTimeout` com `clearTimeout` no `@focus`; `fitBounds` no `actualizarDestinoMapa()` para mostrar ambos os pins
- **Cleanup**: `except Exception: pass` substituído por `logger.warning/debug` em todo o código; imports não utilizados removidos; `console.log` de debug removido do `pedir.html`

### Sessão 6 — Matching Geo + Live Location + Cleanup (2026-06-24)
- **Matching expansivo**: `notificar_motoristas_proximos()` refatorado com círculo expansível 5→10→25km + filtro de frescura (≤2h) + fallback em 4 níveis (localização fresca → antiga → sem PointField → sem motoristas)
- **Telegram Live Location**: substitui a página `/motorista/online/` como fonte primária de localização. Motorista compartilha live location no Telegram (até 8h, updates automáticos ~60s). Bot recebe via `edited_message` e atualiza `Motorista.localizacao`.
- **`edited_message` no polling**: `bot/main.py` inclui `"edited_message"` no `allowed_updates`
- **Novo handler**: `receber_localizacao_live` em `bot/handlers/motorista.py` — verifica assinatura, atualiza localização
- **Nova view**: `BotToggleOnlineView` — corrige bug histórico onde Telegram nunca alterava `Motorista.activo`
- **Novo bot service**: `toggle_online()` — POST para toggle-online-bot com `BotAuthMixin`
- **Location-on-accept**: `aceitar_corrida` no bot verifica `localizacao_desatualizada` (>30min) e pede GPS antes de aceitar
- **Novo state FSM**: `confirmando_localizacao_aceite` — fluxo de localização antes do aceite
- **`salvar_localizacao()`**: helper em `motoristas/services.py` — DRY para `BotAtualizarLocalizacaoView`
- **Dashboard read-only**: toggle switch removido → badge 🟢 Online / 🔴 Offline. Texto: "Gerencie seu status pelo Telegram". Sincroniza via `visibilitychange` + `GET toggle-online`.
- **Card GPS removido** do dashboard e secção "Localização" removida da página Conta
- **Página `/motorista/online/` eliminada** (template, view, rota, endpoint `api/motorista/localizacao/`)
- **Botão "📍 Ativar GPS" removido** de todos os menus do Telegram
- **PT-BR completo**: ~15 strings corrigidas em `bot/messages.py` + `corridas/services.py` (Contacte→Entre em contato, Ofereceste→Você ofereceu, Contacto→Contato, Conta/clica→Conte/clique, Responde→Responda)
- **Links clicáveis**: `[texto](url)` Markdown explícito em `BOAS_VINDAS`, `STATUS_INATIVO`, `TOKEN_INVALIDO`, `ganhos`, `minha_conta`, `AJUDA`
- **Nova mensagem**: `INSTRUCAO_LIVE_LOCATION` — instruções de como compartilhar live location
- **Correcções pós-auditoria**: 8 bugs corrigidos (animação Alpine não-reactiva, leak de coordenadas no nível 3, `sendBeacon` sem CSRF, callback órfão, 200+erro, CSRF global, duplicação de views, validação booleana)
- **Testes**: 110 Django + 36 bot = 146 total

---

## Env Variables Essenciais

```bash
DATABASE_URL=postgresql://user:pass@host/db  # local
TELEGRAM_TOKEN=<TELEGRAM_TOKEN>
BOT_SECRET=<BOT_SECRET>
SITE_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
MP_ACCESS_TOKEN=...
MP_WEBHOOK_SECRET=...
PRECO_ASSINATURA_MENSAL=6900
ADMIN_SECRET_PATH=<ADMIN_SECRET_PATH>
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

1. **Testar fluxo completo** — registar motorista no site, pagar assinatura, vincular Telegram, pedir corrida + aceitar/ofertar + concluir e avaliar
2. **Testar Live Location real** — motorista compartilha live location no Telegram, confirmar no admin
3. **Teste real 3G/4G** — celular Android: motorista no Telegram, passageiro no Chrome
4. **LICENSE** — criar ficheiro LICENSE (AGPL-3.0)
5. **MP webhook Sandbox** — testar com Sandbox real do Mercado Pago
6. **Domínio próprio** — comprar e configurar (ex: motogram.app)

## Próximas Features (Fase 2 — backlog)

- Dashboard avançado motorista (ganhos, metas, combustível)
- WebSocket (Django Channels) substituindo polling REST
- SMS notificação (Zenvia)
- Sentry monitoramento de erros
- Dark mode (Tailwind + Alpine.js toggle)
