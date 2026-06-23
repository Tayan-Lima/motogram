# ARCHITECTURE.md — Motogram GO

## Visão Geral

O MotoGram é composto por três sistemas que comunicam entre si via API REST e webhooks:

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTES                                  │
│                                                                  │
│  [Passageiro]          [Motorista]            [Admin]            │
│  Site mobile-first     Telegram Bot           Site admin         │
│  (browser, sem app)    (recebe corridas)      (painel gestão)    │
└────────┬───────────────────┬──────────────────────┬─────────────┘
         │                   │                      │
         ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND DJANGO (API)                          │
│                                                                  │
│  /api/corridas/    /api/motoristas/    /api/assinaturas/         │
│  /api/webhook/pix  /api/admin/         /api/bot/                 │
│                                                                  │
│  Django 5 + DRF                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   [PostgreSQL]       [Redis]      [Telegram API]
   Supabase           Upstash      Bot via aiogram 3
   (dados)            (cache/fila) (notificações)
```

---

## Componentes

### 1. Site Mobile-First (Django Templates + Alpine.js)

**Páginas públicas**
- `/` — Landing page com marca MotoGram
- `/passageiro` — Interface de pedido de corrida
- `/motorista/cadastro` — Registo de novo motorista
- `/motorista/login` — Acesso à conta

**Páginas autenticadas (passageiro)**
- `/passageiro/perfil` — Perfil, foto, endereços favoritos, histórico de corridas

**Páginas autenticadas (motorista)**
- `/motorista/dashboard` — Ganhos, metas, métricas
- `/motorista/historico` — Lista de corridas
- `/motorista/conta` — Assinatura, renovação, link Telegram

**Páginas admin**
- `/{PREFIX}/` — Dashboard admin (MRR, gráfico 7d, métricas)
- `/{PREFIX}/cadastros/` — KYC — aprovar/reprovar/suspender motoristas
- `/{PREFIX}/motoristas/` — CRM — lista de motoristas com busca
- `/{PREFIX}/motoristas/{id}/` — Detalhe do motorista (dados + histórico)
- `/{PREFIX}/passageiros/` — CRM — lista de passageiros
- `/{PREFIX}/passageiros/{id}/` — Detalhe do passageiro (dados + histórico)
- `/{PREFIX}/corridas/` — Histórico geral com busca e paginação
- `/{PREFIX}/assinaturas/` — Dashboard de assinaturas (activas, MRR, vencendo)
- `/{PREFIX}/avaliacoes/motoristas/` — Avaliações recebidas pelos motoristas
- `/{PREFIX}/avaliacoes/passageiros/` — Avaliações recebidas pelos passageiros
- `/{PREFIX}/avaliacoes/comentarios/` — Comentários de avaliações (moderação)

**Stack frontend**
- Django Templates (server-side rendering — mais simples, menos JS)
- Alpine.js para interactividade leve (sem React, sem build step)
- Tailwind CSS via CDN
- Leaflet.js para mapas (open source, sem custo)

**Por que não React/Flutter para o site?**
Com OpenCode/VibeCoding, Django Templates + Alpine.js gera menos fricção, funciona bem offline-first e é mais fácil de manter sem programador dedicado.

---

### 2. Bot Telegram (aiogram 3)

Processo Python separado que corre em paralelo ao Django. Comunica com o backend via chamadas HTTP internas.

**Fluxo de estados do bot**

```
/start
  ├── "Sou passageiro" → pede localização → envia ao backend → aguarda corrida
  └── "Sou motorista"
        ├── assinatura activa → recebe corridas disponíveis
        └── assinatura inactiva → envia link de renovação

Nova corrida disponível (backend notifica bot)
  └── bot envia para motoristas próximos com botões [✅ Aceitar R$ X] [💬 Oferecer outro] [❌ Recusar]
        ├── Aceitar → cria Oferta (tipo=aceite) → passageiro escolhe
        ├── Oferecer → motorista digita valor → cria Oferta (tipo=contra_oferta)
        └── Recusar → envia para próximo motorista na fila

Passageiro escolhe motorista
  └── motorista escolhido recebe: localização + botões [🏍️ Iniciar] [❌ Cancelar]
        ├── Iniciar → status='em_curso' → botão muda para [✅ Concluir corrida]
        └── Cancelar → status='cancelada' → notifica passageiro

Motorista conclui corrida
  └── bot envia avaliação pós-corrida: 1-5⭐
        ├── 3-5★ → avaliação registada
        └── 1-2★ → pede comentário (obrigatório) → avaliação registada
```

**Comandos disponíveis**
- `/start` — inicia conversa / regista utilizador
- `/corrida` — pede corrida (passageiro)
- `/status` — ver estado da assinatura (motorista)
- `/ganhos` — resumo de ganhos do dia (motorista)
- `/renovar` — link para renovar assinatura (motorista)
- `/ajuda` — lista de comandos
- Botão "🧹 Limpar Chat" — apaga mensagens antigas do chat

---

### 3. Backend Django

#### Modelos principais

```python
# Utilizador base
class Utilizador(AbstractUser):
    telefone = CharField()
    tipo = CharField(choices=['passageiro', 'motorista', 'admin'])
    telegram_id = BigIntegerField(null=True, unique=True)
    telegram_token = CharField(null=True)           # token temporário de activação
    telegram_token_expiry = DateTimeField(null=True)
    email_confirmado = BooleanField(default=False)
    email_token = CharField(blank=True)              # token confirmação email
    email_token_expiry = DateTimeField(null=True)
    foto = ImageField(null=True)                     # foto de perfil

# Motorista — extensão do utilizador
class Motorista(Model):
    utilizador = OneToOneField(Utilizador)
    modelo_moto = CharField()
    placa = CharField()
    foto_cnh = ImageField()
    activo = BooleanField(default=False)
    assinatura_ate = DateField(null=True)
    consumo_km_l = FloatField(default=35.0)    # para cálculo de combustível

# Corrida
class Corrida(Model):
    passageiro = ForeignKey(Utilizador)
    motorista = ForeignKey(Motorista, null=True)
    origem_lat = FloatField()
    origem_lon = FloatField()
    origem_texto = CharField(blank=True)             # endereço legível (ex: "Rua X, 123")
    destino_lat = FloatField(null=True)
    destino_lon = FloatField(null=True)
    destino_texto = CharField(blank=True)            # endereço legível do destino
    distancia_km = FloatField(null=True)             # calculado via Haversine ao concluir
    valor = DecimalField(null=True)                   # negociado via InDrive (Oferta)
    status = CharField(choices=[
        'aguardando', 'aceite', 'em_curso', 'concluida', 'cancelada', 'sem_motoristas'
    ])
    criada_em = DateTimeField(auto_now_add=True)
    aceite_em = DateTimeField(null=True)
    iniciada_em = DateTimeField(null=True)            # momento em que motorista iniciou
    concluida_em = DateTimeField(null=True)
    notificacao_msg_ids = JSONField(default=dict)     # message_id das notificações Telegram

# Oferta (negociação InDrive)
class Oferta(Model):
    corrida = ForeignKey(Corrida, related_name='ofertas')
    motorista = ForeignKey(Motorista)
    valor = DecimalField()
    tipo = CharField(choices=['aceite', 'contra_oferta'])
    status = CharField(choices=['pendente', 'aceita', 'rejeitada'])
    criada_em = DateTimeField(auto_now_add=True)

# Avaliação (1-5★ pós-corrida)
class Avaliacao(Model):
    corrida = ForeignKey(Corrida, related_name='avaliacoes')
    avaliador = ForeignKey(Utilizador, related_name='avaliacoes_feitas')
    avaliado = ForeignKey(Utilizador, related_name='avaliacoes_recebidas')
    tipo = CharField(choices=['pm', 'mp'])           # passageiro→motorista, motorista→passageiro
    nota = PositiveSmallIntegerField()
    comentario = TextField(blank=True)
    criada_em = DateTimeField(auto_now_add=True)
    # UniqueConstraint(corrida, tipo) — uma avaliação por tipo por corrida

# Assinatura
class Assinatura(Model):
    motorista = ForeignKey(Motorista)
    valor = DecimalField()
    pix_txid = CharField()                          # ID da transacção Mercado Pago
    status = CharField(choices=['pendente', 'paga', 'expirada'])
    paga_em = DateTimeField(null=True)
    valida_ate = DateField(null=True)
    criada_em = DateTimeField(auto_now_add=True)
```

#### Endpoints principais

```
POST /api/corridas/                  → cria pedido de corrida (bot)
POST /api/corridas/web/              → cria pedido de corrida (site, requer login + email)
GET  /api/corridas/{id}/status/     → estado da corrida (polling passageiro, público)
POST /api/corridas/{id}/aceitar/     → motorista aceita valor sugerido (bot)
POST /api/corridas/{id}/ofertar/     → motorista faz contra-oferta (bot)
POST /api/corridas/{id}/recusar/     → motorista recusa (bot)
POST /api/corridas/{id}/iniciar/     → motorista inicia corrida (bot)          ← NOVO
POST /api/corridas/{id}/cancelar-motorista/ → motorista cancela (bot)          ← NOVO
POST /api/corridas/{id}/concluir/    → marca corrida como concluída (bot)
POST /api/corridas/{id}/cancelar/    → passageiro cancela (site)
POST /api/corridas/{id}/avaliar/     → passageiro avalia motorista (site)        ← NOVO
POST /api/corridas/{id}/avaliar-passageiro/ → motorista avalia passageiro (bot) ← NOVO
GET  /api/corridas/{id}/ofertas/     → lista motoristas que responderam (site)
POST /api/corridas/{id}/escolher/    → passageiro escolhe motorista (site)

POST /api/motoristas/limpar-mensagens/ → apaga mensagens do chat do motorista (bot) ← NOVO
GET  /api/motoristas/proximos/       → lista motoristas activos num raio (PostGIS)
POST /api/motoristas/cadastro/       → registo de novo motorista
GET  /api/motoristas/dashboard/      → dados para o dashboard (ganhos, metas, km)

POST /api/assinaturas/criar/         → gera QR Code Pix
POST /api/webhook/mercadopago/       → webhook de confirmação de pagamento
POST /api/motoristas/activar-telegram/ → valida token e vincula telegram_id
GET  /api/motoristas/verificar-assinatura/ → verifica assinatura (chamado pelo bot)

GET  /api/map/autocomplete/           → sugestões de endereço (HERE Maps, requer login)  ← NOVO
GET  /api/map/geocode/                → endereço → coordenadas (HERE Maps, requer login) ← NOVO
GET  /api/map/reverse/                → coordenadas → endereço (HERE Maps, requer login) ← NOVO

POST /api/bot/update/                → recebe updates do Telegram (webhook mode, actualmente stub)
```

---

### 4. LibreTaxi — Integração e Adaptação

O MotoGram **não usa o código JavaScript do LibreTaxi directamente**. Usa a sua lógica de negócio como referência e reimplementa em Python/aiogram 3.

**O que é reaproveitado do LibreTaxi (conceptualmente)**

| Conceito LibreTaxi | Implementação MotoGram |
|-------------------|----------------------|
| Máquina de estados do bot | Estados geridos via Redis (aiogram FSM) |
| Matching por geolocalização | PostGIS ST_DWithin no PostgreSQL |
| Negociação de preço | Campo `valor` preenchido pelo passageiro no pedido |
| Pagamento em dinheiro | Mantido — sem pagamento digital na corrida |
| Suporte a múltiplos idiomas | i18n Django (PT-BR por defeito) |

**O que o MotoGram adiciona vs. LibreTaxi**
- Camada de assinaturas (o LibreTaxi é 100% gratuito)
- Site mobile-first com identidade visual
- Dashboard de ganhos do motorista
- Controlo de acesso (só motoristas com assinatura activa recebem corridas)
- Painel administrativo
- Webhook de pagamento Pix

---

## Comunicação Entre Sistemas

### Bot → Backend
```
Bot recebe mensagem Telegram
  → chama endpoints da API Django (ex: /api/corridas/, /api/motoristas/verificar-assinatura/)
  → Django processa e responde com acções
  → Bot executa as acções (envia mensagens, actualiza estado)
```

### Backend → Bot (notificações push)
```
Passageiro faz pedido no site
  → Django guarda corrida
  → Django chama serviço interno: notificar_motoristas(corrida_id)
  → Busca motoristas activos próximos (PostGIS)
  → Para cada motorista: chama Telegram Bot API directamente
    POST https://api.telegram.org/bot{TOKEN}/sendMessage
    { chat_id: motorista.telegram_id, text: "Nova corrida!", ... }
```

### Mercado Pago → Backend (webhook)
```
Motorista paga Pix no site
  → Mercado Pago envia POST /api/webhook/mercadopago/
  → Django valida assinatura do webhook
  → Actualiza assinatura para 'paga'
  → Define motorista.activo = True e assinatura_ate = hoje + 30 dias
  → Gera token único de activação Telegram
  → Envia link t.me/motogram_bot?start={token} por SMS (via Twilio) ou mostra no site
```

### Passageiro → Corrida em tempo real
```
Passageiro submete pedido no site
  → Django cria corrida com status='aguardando'
  → Site faz polling a GET /api/corridas/{id}/ a cada 5 segundos
  → Quando motorista aceita: status muda para 'aceite'
  → Site mostra nome e contacto do motorista ao passageiro
```

---

## Infraestrutura

| Componente | Serviço | Custo |
|-----------|---------|-------|
| Backend Django | Railway | ~$5/mês |
| Base de dados | Supabase (PostgreSQL + PostGIS) | Gratuito (500MB) |
| Cache/fila | Upstash Redis | Gratuito (10k req/dia) |
| Bot Telegram | Railway (processo separado) | Incluído no plano |
| Ficheiros (fotos CNH) | Supabase Storage | Gratuito (1GB) |
| Domínio | Registro.br | ~R$ 40/ano |
| Pagamentos | Mercado Pago | 0.99% por transacção Pix |

**Total estimado: < R$ 100/mês para os primeiros 50 motoristas**

---

## Decisões de Arquitectura

**Por que Django Templates em vez de React?**
Menos complexidade de build, funciona bem com conexão lenta (server-side rendering), mais fácil de manter com OpenCode.

**Por que aiogram 3 em vez de Node.js (como o LibreTaxi)?**
Stack Python unificado com o Django. Menos contexto de mudança para o OpenCode.

**Por que polling no site do passageiro em vez de WebSocket?**
WebSocket exige Django Channels + Redis. Para MVP, polling a cada 5 segundos é suficiente e muito mais simples de implementar. Migra para WebSocket na Fase 2.

**Por que Mercado Pago em vez de Stripe?**
Pix é o método de pagamento natural no Brasil. Mercado Pago tem SDK Python maduro e é familiar para utilizadores brasileiros sem cartão internacional.

---

## Mapas — OpenStreetMap + Leaflet.js

O MotoGram não usa Google Maps. A escolha é **Leaflet.js + OpenStreetMap**, por três razões:

- Gratuito e sem API key — sem risco de bloqueio por exceder quota
- Tiles cacheados pelo browser após primeira visita — funciona parcialmente offline
- Dados do interior do Brasil no OSM são completos o suficiente para cidades pequenas

```
Leaflet.js (142KB, carregado lazy)
    └── Tiles servidos por: tile.openstreetmap.org
          └── Cached pelo browser após primeira visita
          └── Fallback: tiles pré-gerados localmente para a cidade (offline)
```

**Configuração no template:**

```html
<!-- Leaflet só carrega quando utilizador pede o mapa — não no load inicial -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js" defer></script>

<div id="mapa" style="height:280px; display:none;"></div>

<script>
function abrirMapa() {
  document.getElementById('mapa').style.display = 'block';
  const mapa = L.map('mapa', {
    zoomAnimation: false,   // desactivar animações — economiza CPU
    fadeAnimation: false,
  });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    crossOrigin: true,      // necessário para cache do service worker
  }).addTo(mapa);
  // Centrar na localização do utilizador
  mapa.locate({ setView: true, maxZoom: 16 });
}
</script>
```

**Link de localização enviado ao motorista via Telegram:**
```python
# Abre Google Maps se instalado, browser se não — melhor para navegar de moto
def link_localizacao(lat, lon):
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=17"
```

---

## Arquitectura para Internet Fraca (Região Amazónica)

O perfil de conexão típico no interior do Amazonas:
- 3G com 500ms–2000ms de latência
- Sinal intermitente — cai e reconecta com frequência
- Android 2–4GB RAM, Chrome como browser principal

Cada decisão técnica do MotoGram foi tomada com este perfil em mente.

### Camada 1 — Tamanho de payload

```
Página inicial do passageiro:   < 15KB HTML (server-side rendered)
CSS Tailwind (CDN, cached):     < 30KB (zero após primeira visita)
Alpine.js (CDN, cached):        3KB
Leaflet.js (lazy, só no mapa):  142KB (só quando necessário)
─────────────────────────────────────────────────────
Total primeira visita:          < 200KB
Total visitas seguintes:        < 5KB (só dados, resto do cache)
```

### Camada 2 — Server-Side Rendering obrigatório

O Django renderiza HTML completo antes de enviar ao browser.
O passageiro vê a página mesmo que o JS ainda não tenha carregado.

```
Sem SSR (React SPA):   browser recebe HTML vazio → executa JS → faz fetch → mostra conteúdo
                       3 round-trips em 3G = 1500ms–6000ms até ver algo

Com SSR (Django):      browser recebe HTML completo → mostra imediatamente
                       1 round-trip = 500ms–2000ms até ver algo
```

### Camada 3 — Polling com backoff adaptativo

O site do passageiro verifica o estado da corrida periodicamente.
O intervalo aumenta automaticamente se não houver resposta — economiza dados e bateria.

```
0–30s:   polling a cada 5s   (motorista tipicamente aceita neste período)
30s–5m:  polling a cada 15s  (conexão fraca — reduz pressão na rede)
> 5min:  timeout — mostra mensagem e para de fazer polling
```

### Camada 4 — Service Worker (cache offline)

Registado na primeira visita. A partir daí:
- Assets estáticos (CSS, JS, tiles do mapa): servidos do cache local instantaneamente
- Chamadas à API: tentam rede primeiro, cache como fallback
- Se cair a internet durante o aguardo: banner discreto + retoma automaticamente

### Camada 5 — Formulários resilientes

Todos os formulários funcionam como POST HTML puro, sem depender de JS.
O JS intercepta e melhora a experiência quando disponível — mas não é obrigatório.

```
Sem JS:  form submete → Django processa → redireciona → página de aguardo
Com JS:  Alpine.js intercepta → fetch assíncrono → actualiza só o necessário
```

### Camada 6 — Endpoint de status mínimo

O endpoint de polling retorna o mínimo de dados possível:

```python
# Resposta quando aguardando: 27 bytes
{"status": "aguardando"}

# Resposta quando aceite: ~150 bytes
{"status": "aceite", "motorista": {"nome": "João", "telefone": "92999999999", "moto": "CG 160 Vermelha"}}
```

Nunca retornar dados desnecessários no polling — cada byte conta em 3G.

---

## Comunicação Site do Passageiro → Telegram do Motorista

Este é o fluxo central do MotoGram. As duas interfaces (site e Telegram) nunca comunicam directamente — o Django é sempre o intermediário.

```
SITE PASSAGEIRO          DJANGO BACKEND            TELEGRAM MOTORISTA
(Chrome/3G)              (Railway/Python)           (App Telegram)

1. POST /passageiro/pedir/
   {lat, lon, telefone}
        │
        ▼
2.              Cria Corrida(status='aguardando')
                        │
                        ▼
3.              PostGIS: busca motoristas
                activos num raio de 5km
                ORDER BY distancia LIMIT 5
                        │
                        ▼
4.              Para cada motorista:
                POST api.telegram.org/sendMessage
                {
                  chat_id: motorista.telegram_id,
                  text: "🏍️ Nova corrida! 2.3km",
                  reply_markup: {
                    inline_keyboard: [
                      ["✅ Aceitar", "❌ Recusar"]
                    ]
                  }
                }
                        │                                    │
                        ▼                                    ▼
5. Retorna corrida_id                          5. Motorista vê notificação
   ao browser                                    no Telegram

6. Browser começa polling
   GET /api/corridas/{id}/status/
   a cada 5s
                                                 6. Motorista clica ✅ Aceitar
                                                         │
                        ◄────────────────────────────────┘
                        POST /api/corridas/{id}/aceitar/
                        (chamado pelo LibreTaxi/aiogram)
                        │
                        ▼
7.              Corrida.status = 'aceite'
                Corrida.motorista = João
                        │
                        ▼
8.              Envia confirmação ao motorista:
                POST api.telegram.org/sendMessage
                {
                  chat_id: motorista.telegram_id,
                  text: "✅ Corrida confirmada!\n
                         📞 Passageiro: (92) 99999-9999\n
                         📍 [Ver no mapa](maps.google.com?q=-3.1,-60.0)"
                }

9. Polling detecta status='aceite'
   Página mostra:
   ✅ João Silva
   📞 (92) 99999-9999
   🏍️ CG 160 Vermelha
```

### Ponto crítico — o Django envia as mensagens Telegram directamente

O Django não precisa do processo do bot para enviar mensagens ao motorista.
Chama a API HTTP do Telegram directamente:

```python
# backend/corridas/services.py
import requests
import os

def notificar_motoristas_proximos(corrida):
    """Chamado imediatamente após criar uma corrida."""
    motoristas = buscar_motoristas_proximos(
        lat=corrida.origem_lat,
        lon=corrida.origem_lon,
        raio_km=5
    )

    token = os.environ.get('TELEGRAM_TOKEN')

    for motorista in motoristas[:5]:  # máximo 5 notificações por corrida
        distancia = motorista.distancia_km  # anotado pelo PostGIS
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": motorista.telegram_id,
                "text": (
                    f"🏍️ *Nova corrida!*\n\n"
                    f"📍 Distância: {distancia:.1f} km\n"
                    f"🕐 Agora mesmo\n\n"
                    f"Responde rápido!"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "✅ Aceitar", "callback_data": f"aceitar:{corrida.id}"},
                        {"text": "❌ Recusar", "callback_data": f"recusar:{corrida.id}"}
                    ]]
                }
            },
            timeout=5  # não bloquear o request do passageiro mais de 5s
        )
```

### O que o processo bot (LibreTaxi/aiogram) faz neste fluxo

O bot recebe os callbacks dos botões Telegram (aceitar/recusar) e repassa ao Django:

```
Motorista clica ✅ no Telegram
    → Telegram envia callback_query ao bot
    → Bot identifica: callback_data = "aceitar:42"
    → Bot chama: POST /api/corridas/42/aceitar/ (Django)
    → Django actualiza status e envia confirmações
    → Bot responde ao Telegram: edita mensagem para "✅ Aceito!"
```

Esta separação é intencional: o Django controla o estado, o bot só faz a ponte com o Telegram.
