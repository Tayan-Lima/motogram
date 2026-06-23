# PASSENGER_APP.md — Interface do Passageiro

Arquitectura detalhada do site mobile-first do passageiro, optimizado para internet fraca
na região Amazónica (3G instável, latência alta, dispositivos Android de entrada).

---

## 1. Princípios de Design para Internet Fraca

### O problema real

No interior do Amazonas, um utilizador típico tem:
- Conexão 3G com 500ms–2000ms de latência
- Sinal intermitente — pode cair a meio de uma operação
- Android com 2GB RAM e armazenamento limitado
- Chrome como browser principal (já instalado, sem fricção)

### Regras de ouro da arquitectura

```
1. Cada página deve carregar em menos de 3 segundos em 3G
2. Nenhuma acção crítica depende de JS para funcionar
3. O mapa só carrega quando o utilizador clica — nunca no load inicial
4. Imagens comprimidas, SVG em vez de PNG sempre que possível
5. Formulários submetem via POST normal como fallback se JS falhar
6. Estado da corrida deve ser visível mesmo com JS desactivado (SSR)
```

---

## 2. Stack Técnica — Justificada para o Contexto

| Tecnologia | Alternativa rejeitada | Porquê a escolha |
|-----------|----------------------|-----------------|
| Django Templates (SSR) | React SPA | SSR envia HTML pronto — browser não precisa de executar JS para ver conteúdo. Crítico em dispositivos lentos. |
| Alpine.js (3KB) | Vue.js (34KB) / React (45KB) | 11x mais leve. Carrega em ~50ms em 3G. |
| Tailwind CSS via CDN | Bootstrap / Material UI | CDN com cache do browser — após primeira visita, zero download. |
| Leaflet.js (142KB) | Google Maps API | Open source, sem custo, sem API key. Tiles do OpenStreetMap. |
| OpenStreetMap tiles | Google Maps tiles | Gratuito, sem limite de requests, funciona offline com cache. |
| Polling HTTP (5s) | WebSocket | WebSocket mantém conexão aberta — problemático com 3G instável que cai e reconecta. Polling é mais resiliente. |
| Service Worker (cache) | Sem cache | Permite que o site funcione parcialmente offline e carregue instantaneamente na segunda visita. |

---

## 3. Arquitectura de Páginas

### Página principal do passageiro (`/passageiro`)

**O que carrega imediatamente (acima do fold):**
```html
<!-- Carrega em <1 segundo — só HTML + CSS inline crítico -->
<div class="tela-inicial">
  <h1>MotoGram</h1>
  <p>Mototáxi rápido na tua cidade</p>

  <!-- Botão principal — funciona sem JS -->
  <button onclick="mostrarMapa()">
    📍 Pedir corrida agora
  </button>
</div>
```

**O que carrega depois (lazy):**
```html
<!-- Mapa só é inicializado quando utilizador clica no botão -->
<!-- Leaflet.js só é carregado nesse momento -->
<div id="mapa" style="display:none">
  <!-- Leaflet inicializado aqui, só quando necessário -->
</div>
```

**Estratégia de carregamento:**
```
Visita inicial:
  1. Django envia HTML completo (SSR) — 0ms de JS necessário para ver conteúdo
  2. CSS Tailwind do CDN — cached após primeira visita
  3. Alpine.js (3KB) — carrega async, não bloqueia render
  4. Leaflet.js (142KB) — só carrega quando utilizador pede o mapa

Visitas seguintes:
  1. Service Worker serve HTML do cache — carrega instantaneamente
  2. Todos os assets CSS/JS servidos do cache local
  3. Só os dados (JSON) são buscados na rede
```

---

## 4. O Mapa — OpenStreetMap + Leaflet

### Por que OpenStreetMap

- Gratuito e sem limite de requests
- Tiles cacheados pelo browser após primeira visualização
- Funciona offline para áreas já visualizadas
- Dados do interior do Brasil são surpreendentemente completos
- Sem necessidade de API key — sem risco de bloqueio

### Configuração Leaflet optimizada para 3G

```javascript
// Inicialização lazy — só executada quando utilizador pede o mapa
function inicializarMapa() {
  // Tiles OpenStreetMap — gratuito
  const osmTiles = L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution: '© OpenStreetMap',
      maxZoom: 18,
      // Crítico para 3G: cache agressivo dos tiles
      crossOrigin: true,
    }
  );

  const mapa = L.map('mapa', {
    center: [-3.1, -60.0], // Centro do Amazonas como default
    zoom: 15,
    // Desactivar animações pesadas — economiza CPU em dispositivos fracos
    zoomAnimation: false,
    fadeAnimation: false,
    markerZoomAnimation: false,
  });

  osmTiles.addTo(mapa);

  // Botão "Usar minha localização" — mais fácil que digitar endereço
  mapa.addControl(L.control.locate({
    position: 'topright',
    flyTo: true,
    strings: { title: "📍 Usar minha localização" }
  }));

  return mapa;
}
```

### Alternativa offline para áreas sem cobertura

```javascript
// Tiles locais como fallback quando sem internet
const localTiles = L.tileLayer(
  '/static/tiles/{z}/{x}/{y}.png',  // tiles pré-baixados para a cidade
  { maxZoom: 16, errorTileUrl: '/static/tile-vazio.png' }
);
```

Para cidades pequenas específicas, é viável pré-gerar os tiles da cidade com `osmium` e servir estaticamente — zero dependência de internet para o mapa da área local.

---

## 5. Fluxo Completo do Passageiro — Passo a Passo

```
PASSO 1 — Acesso
  Passageiro abre link no Chrome (ex: motogram.app/passageiro)
  → Django serve HTML completo via SSR
  → Página visível em <1s mesmo em 3G
  → Sem login obrigatório (reduz fricção)

PASSO 2 — Localização
  Passageiro clica "Pedir corrida"
  → Mapa Leaflet/OSM carrega (lazy)
  → Browser pede permissão de localização (API nativa do Chrome)
  → Marcador posicionado automaticamente
  → Alternativa: campo de texto para endereço (se GPS falhar)
  → Geocoding via HERE Maps API no backend (`/api/map/autocomplete/` + `/api/map/geocode/`),
    nunca no frontend — chave HERE nunca exposta ao cliente

PASSO 3 — Pedido
  Passageiro confirma localização + (opcional) destino
  → Formulário POST simples ao Django
  → Django cria corrida com status='aguardando'
  → Django notifica motoristas via Telegram API (ver secção 7)
  → Django retorna página de aguardo com corrida_id

PASSO 4 — Aguardo
  Página de aguardo mostra:
  "🔍 A procurar mototaxista próximo..."
  → Alpine.js faz polling a GET /api/corridas/{id}/status/ a cada 5s
  → Se sem resposta em 30s: polling pausa, tenta a cada 15s (economiza dados)
  → Timeout de 5 minutos: mostra "Nenhum mototaxista disponível agora"

PASSO 5 — Confirmação
  Motorista aceita no Telegram
  → Django actualiza corrida para status='aceite'
  → Próximo polling do site detecta mudança
  → Página mostra:
    ✅ Mototaxista encontrado!
    👤 João Silva
    📞 (92) 99999-9999
    🏍️ Honda CG 160 — Vermelha
  → Passageiro liga directamente — sem intermediário

PASSO 6 — Conclusão
  Sem tracking automático (economiza dados e bateria)
  Passageiro paga em dinheiro ao motorista
  Motorista conclui a corrida no Telegram (/concluir)
```

---

## 6. Optimizações Específicas para 3G Fraco

### Polling inteligente (backoff adaptativo)

```javascript
// Alpine.js — polling com backoff para economizar dados e bateria
function statusCorrida(corridaId) {
  return {
    status: 'aguardando',
    motorista: null,
    intervalo: 5000,      // começa em 5s
    tentativas: 0,

    async iniciar() {
      while (this.status === 'aguardando') {
        await this.verificar();
        await this.esperar(this.intervalo);

        // Backoff progressivo após 6 tentativas (30s)
        // Reduz consumo de dados quando não há resposta
        if (this.tentativas > 6) this.intervalo = 15000;  // 15s
        if (this.tentativas > 20) this.intervalo = 30000; // 30s
      }
    },

    async verificar() {
      try {
        const r = await fetch(`/api/corridas/${corridaId}/status/`, {
          // Timeout agressivo — não espera mais de 8s por resposta
          signal: AbortSignal.timeout(8000)
        });
        const data = await r.json();
        this.status = data.status;
        this.motorista = data.motorista;
        this.tentativas++;
      } catch (e) {
        // Sem internet momentânea — não crasha, só tenta de novo
        console.log('Sem conexão, tentando novamente...');
      }
    },

    esperar(ms) {
      return new Promise(r => setTimeout(r, ms));
    }
  }
}
```

### Endpoint de status ultra-leve

```python
# Django — resposta mínima para o polling (economiza dados do passageiro)
class CorridaStatusView(View):
    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id)

        if corrida.status == 'aguardando':
            # Resposta mínima — só o necessário
            return JsonResponse({'status': 'aguardando'})

        if corrida.status == 'aceite':
            return JsonResponse({
                'status': 'aceite',
                'motorista': {
                    'nome': corrida.motorista.utilizador.first_name,
                    'telefone': corrida.motorista.utilizador.telefone,
                    'moto': corrida.motorista.modelo_moto,
                    'cor_moto': corrida.motorista.cor_moto,
                }
            })

        return JsonResponse({'status': corrida.status})
```

### Formulário resiliente (funciona sem JS)

```html
<!-- Formulário de pedido funciona mesmo se JS falhar -->
<!-- Sem JS: submit normal → Django processa → redireciona para página de aguardo -->
<!-- Com JS: Alpine.js intercepta e faz fetch assíncrono -->
<form
  method="POST"
  action="/passageiro/pedir/"
  x-on:submit.prevent="submeterPedido"
>
  {% csrf_token %}
  <input type="hidden" name="lat" x-bind:value="lat">
  <input type="hidden" name="lon" x-bind:value="lon">
  <input type="text" name="destino" placeholder="Destino (opcional)">
  <button type="submit">Pedir corrida</button>
</form>
```

### Service Worker — cache para segunda visita instantânea

```javascript
// /static/sw.js — registado na página principal
const CACHE = 'motogram-v1';
const ASSETS = [
  '/',
  '/passageiro',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', e => {
  // Cache-first para assets estáticos
  // Network-first para dados da API
  if (e.request.url.includes('/api/')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
```

---

## 7. Comunicação Site do Passageiro → Telegram do Motorista

**Este é o fluxo mais crítico e o menos documentado anteriormente.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DETALHADO                               │
│                                                                  │
│  Passageiro                Django              Motorista         │
│  (Chrome/3G)               (Railway)           (Telegram)        │
│                                                                  │
│  1. POST /passageiro/pedir/                                      │
│     { lat, lon, destino }                                        │
│         │                                                        │
│         ▼                                                        │
│  2. Django cria Corrida(status='aguardando')                     │
│         │                                                        │
│         ▼                                                        │
│  3. Django busca motoristas activos                              │
│     num raio de 5km (PostGIS)                                    │
│     ORDER BY distancia ASC                                       │
│     LIMIT 5                                                      │
│         │                                                        │
│         ▼                                                        │
│  4. Para cada motorista na lista:                                │
│     POST api.telegram.org/bot{TOKEN}/sendMessage                 │
│     {                                                            │
│       chat_id: motorista.telegram_id,                            │
│       text: "🏍️ Nova corrida!\n                                  │
│              📍 2,3 km de distância\n                            │
│              📌 Bairro: Centro\n                                 │
│              🕐 Aguardando há 0 min",                            │
│       reply_markup: {                                            │
│         inline_keyboard: [[                                      │
│           { text: "✅ Aceitar", callback_data: "aceitar:42" },   │
│           { text: "❌ Recusar", callback_data: "recusar:42" }    │
│         ]]                                                       │
│       }                                                          │
│     }                                                            │
│         │                                                        │
│         ▼                                                        │
│  5. Django retorna corrida_id ao browser do passageiro           │
│     → Browser começa polling /api/corridas/42/status/            │
│                                                                  │
│  6. Motorista vê mensagem no Telegram                            │
│     → Clica ✅ Aceitar                                           │
│     → Telegram envia callback ao LibreTaxi                       │
│     → LibreTaxi chama Django:                                    │
│       POST /api/corridas/42/aceitar/                             │
│       { motorista_telegram_id: 987654 }                          │
│         │                                                        │
│         ▼                                                        │
│  7. Django actualiza Corrida(status='aceite', motorista=João)    │
│                                                                  │
│  8. Próximo polling do passageiro detecta status='aceite'        │
│     → Página mostra dados do motorista                           │
│     → Passageiro liga directamente para o motorista              │
│                                                                  │
│  9. Django envia confirmação ao motorista via Telegram:          │
│     "✅ Corrida confirmada!                                      │
│      📞 Passageiro: (92) 99999-9999                             │
│      📍 Localização: [link Google Maps]"                         │
└─────────────────────────────────────────────────────────────────┘
```

### O link de localização enviado ao motorista

```python
# Django — gera link de localização para o motorista no Telegram
def gerar_link_localizacao(lat, lon, label="Passageiro"):
    # OpenStreetMap — gratuito, sem API key
    osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=17"
    return osm

def mensagem_nova_corrida(corrida, distancia_km):
    return (
        f"🏍️ *Nova corrida disponível!*\n\n"
        f"📍 Distância: {distancia_km:.1f} km\n"
        f"🗺️ [Ver no mapa]({gerar_link_localizacao(corrida.origem_lat, corrida.origem_lon)})\n"
        f"🕐 Pedido há {corrida.minutos_aguardando()} min\n\n"
        f"Responde rápido — outros motoristas também receberam!"
    )
```

---

## 8. Cenários de Falha e Recuperação

### Cenário 1 — Passageiro perde conexão durante aguardo

```
Passageiro aguarda corrida → sinal cai → Alpine.js não consegue fazer polling
  → Service Worker detecta offline
  → Mostra banner: "📶 Sem conexão. Verificando quando voltar..."
  → Quando conexão volta: polling retoma automaticamente
  → Se corrida já foi aceite: mostra dados do motorista imediatamente
```

### Cenário 2 — Nenhum motorista disponível próximo

```
Django busca motoristas → nenhum activo num raio de 5km
  → Não envia notificação Telegram (ninguém para notificar)
  → Retorna corrida com status='sem_motoristas'
  → Site mostra: "😔 Nenhum mototaxista disponível agora.
                  Tenta novamente em alguns minutos."
  → Opção: aumentar raio para 10km e tentar novamente
```

### Cenário 3 — Motorista aceita mas passageiro já saiu do site

```
Passageiro fecha o browser antes da corrida ser aceite
  → Corrida permanece com status='aguardando' no banco
  → Motorista aceita → Django tenta notificar passageiro
  → Passageiro não recebe (não há push notification sem app)
  → Corrida fica órfã
  → Cron job cancela corridas em status='aguardando' há mais de 10 minutos
  → Motorista recebe aviso no Telegram: "❌ Corrida cancelada — passageiro não está mais disponível"
```

### Cenário 4 — Django fora do ar (Railway restart)

```
Passageiro submete pedido → Django retorna erro 502
  → Formulário tem atributo action normal (POST)
  → Browser mostra erro de rede padrão
  → Utilizador tenta de novo após alguns segundos
  (Railway reinicia em <30s na maioria dos casos)
```

---

## 9. Identificação do Passageiro

O passageiro pode usar o MotoGram de duas formas:

**Modo anónimo** — pede corrida sem conta. Só exige telefone (para o motorista ligar) e localização. Sem histórico, sem recuperação de corridas em aberto.

**Modo conta** — cadastro completo com confirmação de telefone via SMS e e-mail. Dá acesso a histórico de corridas, cancelamento de pedido em aberto e perfil guardado.

O cadastro completo está documentado em `ONBOARDING.md` — Parte 1.

**Dados mínimos para pedido anónimo:**
- Número de telefone (obrigatório — para o motorista poder ligar)
- Localização (obrigatório — para o matching)
- Destino (opcional — para referência do motorista)
- Nome (opcional — para o motorista identificar)

Ver todos os fluxos de comunicação em `COMMUNICATION_FLOWS.md`.

---

## 10. Performance — Metas e Medições

| Métrica | Meta | Como medir |
|---------|------|-----------|
| First Contentful Paint | < 1.5s em 3G | Lighthouse com throttling 3G |
| Tamanho total da página inicial | < 50KB | Chrome DevTools Network |
| Tamanho após lazy loading do mapa | < 250KB | Chrome DevTools Network |
| Polling endpoint resposta | < 200ms | Django Debug Toolbar |
| Tempo para corrida ser notificada ao motorista | < 3s | Teste manual |

### Como testar em condições reais de 3G

```bash
# Chrome DevTools → Network → Throttling → Custom
# Configurar: Download 1.5 Mbps / Upload 750 Kbps / Latency 300ms
# Simula 3G típico do interior do AM

# Lighthouse via CLI
npx lighthouse https://motogram.app/passageiro \
  --throttling-method=devtools \
  --output=html \
  --output-path=./lighthouse-report.html
```
