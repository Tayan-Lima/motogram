# AGENTS.md — MotoGram

Instruções para agentes de IA (OpenCode, Claude Code, Cursor) que trabalham neste repositório.

---

## O Projecto

MotoGram é uma plataforma de mototáxi para cidades pequenas no Brasil. Combina:
- **Bot Telegram** (aiogram 3) — interface operacional para motoristas e passageiros
- **Site mobile-first** (Django Templates + Alpine.js) — dashboard do motorista, pedidos do passageiro, painel admin
- **Backend Django** (Django 5 + DRF) — API REST, lógica de negócio, webhooks
- **PostgreSQL + PostGIS** (Supabase) — dados e buscas geoespaciais
- **Redis** (Upstash) — cache de sessões e estados do bot (FSM)

Lê o `ARCHITECTURE.md` antes de qualquer tarefa que envolva criar novos ficheiros ou modificar a estrutura do projecto.

---

## Stack e Versões

```
Python         3.12
Django         5.x
djangorestframework  3.15.x
aiogram        3.x
psycopg2       2.9.x
redis          5.x
Pillow         10.x
requests       2.31.x
python-dotenv  1.x
gunicorn       21.x
```

Frontend (via CDN, sem build step):
```
Tailwind CSS   3.x  (CDN)
Alpine.js      3.x  (CDN)
Leaflet.js     1.9  (CDN)
```

---

## Estrutura do Repositório

```
motogram/
├── backend/                  # Projecto Django
│   ├── motogram/             # Settings, urls, wsgi
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── corridas/             # App de corridas
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── motoristas/           # App de motoristas e assinaturas
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── pagamentos/           # Integração Mercado Pago
│   │   ├── views.py          # Webhook handler
│   │   └── services.py       # Lógica de criação de Pix
│   ├── site_publico/         # Views do site mobile-first
│   │   ├── views.py
│   │   └── urls.py
│   ├── templates/            # HTML templates
│   │   ├── base.html
│   │   ├── passageiro/
│   │   ├── motorista/
│   │   └── admin_mg/
│   └── manage.py
├── bot/                      # Processo do bot Telegram (separado)
│   ├── main.py               # Entry point do bot
│   ├── handlers/
│   │   ├── passageiro.py     # Handlers do fluxo do passageiro
│   │   ├── motorista.py      # Handlers do fluxo do motorista
│   │   └── corridas.py       # Handlers de aceitar/recusar corridas
│   ├── services.py           # Chamadas à API do backend
│   └── states.py             # Definição de estados FSM (aiogram)
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md             # Este ficheiro
│   ├── ROADMAP.md
│   ├── CONVENTIONS.md
│   └── TESTING.md
├── .env.example
├── requirements.txt
├── Procfile                  # Railway: web + bot como processos separados
└── README.md
```

---

## Regras para o Agente

### SEMPRE

1. **Ler o ARCHITECTURE.md antes de criar novos modelos ou endpoints.** Os modelos principais já estão definidos — não duplicar.

2. **Usar variáveis de ambiente para todas as credenciais.** Nunca hardcodar tokens, senhas ou chaves no código.
```python
# ✅ Correcto
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# ❌ Errado
TELEGRAM_TOKEN = "1234567890:ABCdef..."
```

3. **Verificar assinatura activa antes de qualquer acção do motorista.**
```python
# Em qualquer view ou handler que envolva o motorista
if not motorista.activo or motorista.assinatura_ate < date.today():
    return Response({'erro': 'Assinatura inactiva'}, status=403)
```

4. **Usar PostGIS para buscas geográficas.** Nunca calcular distâncias em Python com loops.
```python
# ✅ Correcto — PostGIS
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point

ponto = Point(longitude, latitude, srid=4326)
motoristas = Motorista.objects.filter(
    activo=True,
    localizacao__dwithin=(ponto, 0.05)  # ~5km
).annotate(distancia=Distance('localizacao', ponto)).order_by('distancia')

# ❌ Errado — calcular em Python
for m in Motorista.objects.all():
    if calcular_distancia(m.lat, m.lon, lat, lon) < 5:
        ...
```

5. **Bot e backend comunicam via HTTP interno.** O bot nunca acede directamente à base de dados.
```python
# ✅ Correcto — bot chama API Django
response = requests.post(
    f"{BACKEND_URL}/api/corridas/{corrida_id}/aceitar/",
    headers={"X-Bot-Secret": BOT_SECRET},
    json={"motorista_telegram_id": message.from_user.id}
)

# ❌ Errado — bot importa modelos Django
from corridas.models import Corrida
```

6. **Validar webhook do Mercado Pago.** Verificar sempre a assinatura do webhook antes de processar.

7. **Tokens de activação Telegram têm validade de 24 horas** e são de uso único — apagar após validação.

---

### NUNCA

- Nunca usar `Django.contrib.admin` como painel de administração para utilizadores finais — usar as views em `/admin_mg/`
- Nunca retornar dados sensíveis (telegram_id, tokens) em endpoints públicos
- Nunca fazer chamadas ao Telegram API directamente nas views Django — usar o serviço `corridas/services.py`
- Nunca usar `FloatField` para coordenadas GPS nos modelos — usar `PointField` do PostGIS
- Nunca usar `requirements.txt` com versões fixas sem testar (`==` é obrigatório em produção)
- Nunca usar Google Maps API — usar sempre Leaflet.js + OpenStreetMap (gratuito, sem API key)
- Nunca carregar Leaflet.js no load inicial da página — carregar lazy só quando o mapa for pedido
- Nunca retornar dados desnecessários nos endpoints de polling — resposta mínima (< 200 bytes)
- Nunca usar React, Vue ou qualquer framework com build step no site do passageiro — Alpine.js via CDN apenas
- Nunca bloquear o request do passageiro esperando resposta do Telegram — chamar Telegram API em background (timeout=5s)

### REGRAS DE PERFORMANCE (internet fraca)

8. **Página inicial do passageiro deve ter < 15KB de HTML.** Server-side rendering obrigatório — Django renderiza tudo antes de enviar.

9. **Leaflet.js é carregado lazy.** Nunca incluir no `<head>` — só carregar quando `abrirMapa()` for chamado.

10. **Polling com backoff adaptativo.** Começar em 5s, aumentar para 15s após 30s sem resposta, 30s após 5 minutos. Ver implementação em `PASSENGER_APP.md`.

11. **Service Worker obrigatório no site do passageiro.** Ficheiro `/static/sw.js` deve ser registado na landing page para cache offline.

12. **Notificações Telegram enviadas em paralelo.** Usar `threading.Thread` ou `asyncio.gather` para notificar múltiplos motoristas simultaneamente — nunca em loop sequencial.

---

## Padrões de Código

### Views Django (API)
```python
# Padrão para views com verificação de assinatura
class CorridaAceitarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, corrida_id):
        motorista = get_object_or_404(Motorista, utilizador=request.user)

        if not motorista.assinatura_activa:
            return Response(
                {'erro': 'Renova a tua assinatura para aceitar corridas.',
                 'link': 'https://motogram.app/motorista/conta'},
                status=status.HTTP_403_FORBIDDEN
            )

        corrida = get_object_or_404(Corrida, id=corrida_id, status='aguardando')
        corrida.motorista = motorista
        corrida.status = 'aceite'
        corrida.aceite_em = timezone.now()
        corrida.save()

        return Response(CorridaSerializer(corrida).data)
```

### Handlers do Bot (aiogram 3)
```python
# Padrão para handlers com verificação de estado
@router.callback_query(F.data.startswith("aceitar_corrida:"))
async def aceitar_corrida(callback: CallbackQuery):
    corrida_id = callback.data.split(":")[1]

    response = await backend_service.aceitar_corrida(
        corrida_id=corrida_id,
        telegram_id=callback.from_user.id
    )

    if response.get('erro'):
        await callback.answer(response['erro'], show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Corrida aceite!\n"
        f"📍 Passageiro aguarda em {response['origem']}\n"
        f"📞 Contacto: {response['passageiro_telefone']}"
    )
```

### Templates HTML (mobile-first)
```html
<!-- Padrão base para páginas mobile-first -->
<!-- Sempre mobile-first, nunca desktop-first -->
<!-- Usar classes Tailwind com prefixo sm: para desktop -->
<div class="max-w-md mx-auto min-h-dvh flex flex-col">
  <!-- conteúdo -->
</div>
```

---

## Variáveis de Ambiente Necessárias

```bash
# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=.railway.app,motogram.app
DATABASE_URL=postgresql://...

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Redis
REDIS_URL=redis://...

# Telegram
TELEGRAM_TOKEN=
TELEGRAM_WEBHOOK_URL=https://motogram.app/api/bot/update/
BOT_SECRET=  # token interno para comunicação bot→backend

# Mercado Pago
MP_ACCESS_TOKEN=
MP_WEBHOOK_SECRET=

# App
BACKEND_URL=https://motogram.app
PRECO_ASSINATURA_MENSAL=6900  # em centavos = R$ 69,00
```

---

## Fluxo de Desenvolvimento

Ao receber uma tarefa, o agente deve:

1. Identificar qual componente é afectado (`backend/`, `bot/`, `templates/`)
2. Verificar se há modelos existentes que cobrem o caso (ver `ARCHITECTURE.md`)
3. Implementar começando pelos modelos → serializers → views → urls → templates
4. Adicionar testes unitários básicos para lógica de negócio crítica
5. Actualizar o `ROADMAP.md` se a tarefa corresponder a um item da roadmap

---

## Como Correr Localmente

```bash
# 1. Clonar e instalar dependências
git clone https://github.com/teu-user/motogram
cd motogram
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# editar .env com as tuas credenciais

# 3. Migrations
cd backend
python manage.py migrate

# 4. Correr Django
python manage.py runserver

# 5. Correr bot (terminal separado)
cd ../bot
python main.py

# 6. Expor para Telegram (desenvolvimento)
# Instalar ngrok: https://ngrok.com
ngrok http 8000
# Actualizar TELEGRAM_WEBHOOK_URL no .env com o URL do ngrok
```

---

## Deploy (Railway)

O `Procfile` define dois processos:
```
web: cd backend && gunicorn motogram.wsgi:application --bind 0.0.0.0:$PORT --workers 2
bot: cd bot && python main.py
```

Railway corre ambos automaticamente. Variáveis de ambiente são configuradas no dashboard do Railway.
