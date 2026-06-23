# ROADMAP.md — Motogram GO

## Visão Geral das Fases

```
Fase 1 (MVP)     Fase 2 (Crescimento)     Fase 3 (Expansão)
4–6 semanas      4–6 semanas              6–8 semanas
─────────────    ────────────────────     ─────────────────
Bot Telegram     Dashboard avançado       Módulo entregas
Site básico      Metas e combustível      Lojas parceiras
Assinaturas Pix  Avaliações               Mini App Telegram
Matching geo     WebSocket realtime       Multi-cidade
```

---

## Fase 1 — MVP (Semanas 1–6)

> Cada semana inclui testes unitários das features implementadas.
> Dependências entre tarefas marcadas com `→ depende de:`.

### Semana 1: Fundação + Deploy Staging

- [ ] Criar estrutura de pastas: `backend/`, `bot/`, `backend/templates/`
- [ ] Django project: `django-admin startproject motogram backend/`
- [ ] Apps Django: `corridas`, `motoristas`, `pagamentos`, `site_publico`
- [ ] `requirements.txt` (Django 5, DRF, psycopg2, redis, aiogram, Pillow, requests, python-dotenv, gunicorn)
- [ ] `settings.py` com PostGIS, Redis, static files, env vars
- [ ] Modelos: `Utilizador`, `Motorista`, `Corrida`, `Assinatura` (ver `ARCHITECTURE.md`)
- [ ] Migrations + `manage.py migrate` local
- [ ] Deploy staging no Railway + Supabase (validar infra cedo)
- [ ] `.env` configurado com credenciais reais de staging
- [ ] Testes unitários: modelos (assinatura activa/inactiva, criação)

**Feito quando:** `manage.py runserver` funciona local, deploy no Railway responde, modelos criam registros.

### Semana 2: Bot Telegram — Mínimo

→ depende de: modelos Django (Semana 1)

- [ ] `bot/main.py` com aiogram 3 + webhook setup
- [ ] `bot/states.py`: `PassageiroStates`, `MotoristaStates`
- [ ] `bot/services.py`: chamadas HTTP ao backend Django
- [ ] `bot/messages.py`: constantes de mensagens (PT-BR)
- [ ] Handler `/start` — escolha passageiro/motorista
- [ ] Fluxo passageiro: pedir localização → `POST /api/corridas/` → confirmar
- [ ] Fluxo motorista: `/status` mostra estado da assinatura
- [ ] Endpoint Django `POST /api/bot/update/` para receber updates
- [ ] Testes: handler /start, criação de corrida via bot

**Feito quando:** passageiro consegue enviar localização no bot e corrida é criada na BD.

### Semana 3: Matching + Notificações

→ depende de: bot mínimo (Semana 2), modelos (Semana 1)

- [ ] PostGIS: `PointField` em `Motorista`, `ST_DWithin` para matching
- [ ] `corridas/services.py`: `notificar_motoristas_proximos()` — POST api.telegram.org
- [ ] Endpoint `POST /api/corridas/{id}/aceitar/` e `recusar/`
- [ ] Bot: callback handlers para botões ✅ Aceitar / ❌ Recusar
- [ ] Troca de contactos após aceitação (telefone do passageiro → motorista)
- [ ] Endpoint `GET /api/corridas/{id}/status/` (polling do passageiro)
- [ ] Cron job: cancelar corridas aguardando há > 10 min
- [ ] Testes: matching geográfico, aceitar/recusar corrida, webhook Mercado Pago

**Feito quando:** passageiro pede corrida no bot, motorista recebe notificação e aceita, passageiro vê confirmação.

### Semana 4: Site Passageiro

→ depende de: endpoints de corrida (Semana 3)

- [ ] Landing page (`/`) — traduzir `motogram-landing.html` para Tailwind CDN
- [ ] Página de pedido (`/passageiro`) — mapa Leaflet lazy + formulário
- [ ] Polling com backoff adaptativo (5s → 15s → 30s)
- [ ] Página de confirmação com dados do motorista
- [ ] Página de acompanhamento (`/passageiro/acompanhar/`)
- [ ] Service Worker (`/static/sw.js`) para cache offline
- [ ] Formulário resiliente (POST funciona sem JS)
- [ ] Page HTML < 15KB (verificar com Lighthouse)
- [ ] Testes: view de pedido, polling endpoint

**Feito quando:** passageiro pede corrida pelo site, vê estado em tempo real, dados do motorista aparecem.

### Semana 5: Site Motorista + Pagamento

→ depende de: modelos (Semana 1), bot (Semana 2)

- [ ] Cadastro motorista (3 passos): dados pessoais → moto → documentos
- [ ] Upload de documentos (CNH, antecedentes, foto) para Supabase Storage
- [ ] Página de pagamento — geração de QR Code Pix (Mercado Pago)
- [ ] `POST /api/webhook/mercadopago/` — confirmação de pagamento
- [ ] Geração de token único de activação Telegram (24h, uso único)
- [ ] Login do motorista
- [ ] Dashboard: ganhos, toggle online/offline
- [ ] Página de conta: assinatura, link Telegram
- [ ] Testes: cadastro, webhook Pix, activação Telegram

**Feito quando:** motorista cadastra-se, paga Pix, activa Telegram e recebe corridas.

### Semana 6: Admin + Estabilização + Deploy Produção

→ depende de: todas as semanas anteriores

- [ ] Painel admin (`/admin_mg/`): listagem de motoristas (aprovar/bloquear)
- [ ] Painel admin: histórico de corridas
- [ ] Cron job diário: bloquear motoristas com assinatura vencida
- [ ] Notificação automática 3 dias antes do vencimento
- [ ] Testes de ponta a ponta (fluxo completo passageiro + motorista)
- [ ] Deploy estável no Railway (produção)
- [ ] Domínio configurado
- [ ] Checklist de deploy (ver `TESTING.md`)

**Feito quando:** 5 motoristas conseguem cadastrar-se, pagar, ligar o Telegram e receber corridas. 10 passageiros conseguem pedir corrida via site e via bot.

**Critério de conclusão da Fase 1:** ver acima.

---

## Fase 2 — Crescimento (Semanas 7–12)

### Dashboard Avançado do Motorista

- [ ] Ganhos por período (hoje, semana, mês) com gráfico simples
- [ ] Meta mensal — o motorista define o valor, site mostra progresso
- [ ] Cálculo de combustível: motorista define consumo da moto (km/L) e preço actual
- [ ] Lucro líquido estimado (ganhos − combustível)
- [ ] Melhor dia da semana (baseado no histórico)
- [ ] Exportar histórico em CSV

### Qualidade e Segurança

- [x] Sistema de avaliação de passageiros (1–5 estrelas, pelo motorista)
- [ ] Motoristas podem bloquear passageiros problemáticos
- [x] Histórico de avaliações no painel admin
- [ ] Verificação de CNH (upload obrigatório no cadastro)

### Performance

- [ ] Substituir polling por WebSocket (Django Channels) para estado da corrida
- [ ] Cache de motoristas próximos (Redis, TTL 30 segundos)
- [ ] Optimização de queries PostGIS

### Operacional

- [ ] SMS de notificação de vencimento (Twilio ou Zenvia)
- [ ] Relatório semanal automático para o admin (email)
- [ ] Logs de erros centralizados (Sentry free tier)

---

## Fase 3 — Expansão (Semanas 13–20)

### Módulo de Entregas

- [ ] Modelo `Entrega` com campos: loja, itens, endereço de entrega
- [ ] Modelo `Loja` e `Produto`
- [ ] Cardápio no bot: passageiro escolhe loja → lista produtos → confirma pedido
- [ ] Fluxo de entrega no bot: motorista → vai à loja → confirma recolha → entrega
- [ ] Status em tempo real da entrega no site do cliente
- [ ] Painel de gestão para lojas (acesso do dono da loja)

### Lojas Parceiras

- [ ] Cadastro de lojas no painel admin
- [ ] Categorias: Farmácia, Lanche, Mercado, Água & Gás
- [ ] Listagem de lojas próximas no bot por categoria
- [ ] Sistema de comissão ou taxa fixa mensal por loja

### Mini App Telegram

- [ ] Interface do passageiro como Telegram Web App
- [ ] Mapa interactivo dentro do Telegram
- [ ] Identidade visual MotoGram dentro do Telegram
- [ ] Substituição gradual do site público pelo Mini App

### Multi-Cidade

- [ ] Suporte a múltiplas cidades na mesma plataforma
- [ ] Bot separado por cidade ou bot único com selecção de cidade
- [ ] Painel admin por cidade (para franqueados)
- [ ] Relatórios consolidados

---

## Backlog (Sem Data)

- App nativo Flutter para passageiro (Android + iOS — Play Store / App Store)
- App nativo Flutter para motorista
- Pagamento de corrida pelo app (sem cash) via Pix
- Rastreamento GPS em tempo real durante a corrida
- Programa de fidelidade para passageiros frequentes
- API pública para integrações de terceiros
- Planos de assinatura diferenciados (básico / premium)

---

## Priorização

Para cada sprint de 2 semanas, o critério de priorização é:

1. **Bloqueia receita?** → Prioridade máxima
2. **Bloqueia motorista de receber corridas?** → Prioridade alta
3. **Melhora retenção do motorista?** → Prioridade média
4. **Melhora experiência do passageiro?** → Prioridade média
5. **Feature administrativa?** → Prioridade baixa
