# LIBRETAXI_INTEGRATION.md — Motogram GO

O MotoGram usa o [LibreTaxi](https://github.com/ro31337/libretaxi) como **referência de soluções** — não como fork.
O bot é implementado em Python (aiogram 3), mas a lógica de negócio é inspirada no LibreTaxi.

---

## 1. O que é o LibreTaxi

O LibreTaxi é um bot Telegram de código aberto para mototáxi/ride-hailing. Stack original:

```
Go (processo único)
  ├── PostgreSQL (estado dos utilizadores e corridas)
  ├── RabbitMQ (fila interna de mensagens)
  └── Telegram Bot API (interface)
```

**Repositório:** `github.com/ro31337/libretaxi`

---

## 2. O que o MotoGram aprende do LibreTaxi

O MotoGram **não faz fork** do LibreTaxi. Implementa o bot em Python/aiogram 3, mas reutiliza os padrões de lógica:

| Conceito LibreTaxi | Implementação MotoGram |
|---|---|
| Máquina de estados do bot | aiogram FSM + Redis |
| Matching por geolocalização | PostGIS `ST_DWithin` no Django |
| Negociação de preço | Campo `valor` no pedido do passageiro |
| Suporte a múltiplos idiomas | i18n Django (PT-BR por defeito) |
| Envio de localização/contacto | Telegram API via `requests` |

**O que o MotoGram adiciona:**
- Camada de assinaturas (LibreTaxi é gratuito)
- Site mobile-first com identidade visual
- Dashboard de ganhos do motorista
- Webhook de pagamento Pix
- Painel administrativo

---

## 3. Padrões do LibreTaxi para implementar em aiogram 3

### 3.1 Verificação de assinatura antes de cada acção

O LibreTaxi verifica se o motorista tem assinatura activa antes de permitir qualquer acção. No MotoGram, isso é um middleware em aiogram:

```python
# bot/middlewares/subscription.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import os, requests

class SubscriptionMiddleware(BaseMiddleware):
    """Verifica assinatura activa antes de qualquer acção do motorista."""

    async def __call__(self, handler, event, data):
        telegram_id = event.from_user.id
        django_url = os.environ.get("BACKEND_URL")
        bot_secret = os.environ.get("BOT_SECRET")

        resp = requests.get(
            f"{django_url}/api/motoristas/verificar-assinatura/",
            params={"telegram_id": telegram_id},
            headers={"X-Bot-Secret": bot_secret},
            timeout=5,
        )

        status = resp.json()
        if not status.get("active"):
            if isinstance(event, Message):
                await event.answer(
                    f"❌ {status.get('message', 'Assinatura inactiva.')}\n\n"
                    f"Renova em: {status.get('link', 'motogram.app/motorista/conta')}"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(status.get("message", "Assinatura inactiva"), show_alert=True)
            return  # bloqueia o handler

        return await handler(event, data)
```

### 3.2 Matching geográfico

O LibreTaxi faz matching interno. No MotoGram, o Django faz isso com PostGIS — o bot só chama a API:

```python
# bot/services.py
# NOTA: o bot actualmente usa requests síncrono (não async).
# O exemplo abaixo usa async para referência conceitual.
# O código real está em bot/services.py com requests.get() síncrono.
async def buscar_motoristas_proximos(lat: float, lon: float, raio_km: float = 5):
    resp = requests.get(
        f"{BACKEND_URL}/api/motoristas/proximos/",
        params={"lat": lat, "lon": lon, "raio": raio_km},
        headers={"X-Bot-Secret": BOT_SECRET},
        timeout=5,
    )
    return resp.json()
```

### 3.3 Negociação de preço

O LibreTaxi permite que passageiro e motorista negociem o preço. No MotoGram, o passageiro define o valor ao pedir a corrida (campo `valor`). Motorista vê o valor e decide aceitar ou recusar.

### 3.4 Gestão de estados (FSM)

O LibreTaxi usa FSM interno. No MotoGram, aiogram FSM + Redis:

```python
# bot/states.py
from aiogram.fsm.state import State, StatesGroup

class PassageiroStates(StatesGroup):
    aguardando_localizacao = State()
    aguardando_destino = State()
    aguardando_motorista = State()
    em_corrida = State()

class MotoristaStates(StatesGroup):
    inativo = State()
    disponivel = State()
    em_corrida = State()
```

---

## 4. Endpoints Django que o bot chama

O bot aiogram chama estes endpoints do Django via HTTP:

| Endpoint | Método | Descrição |
|---|---|---|
| `/api/corridas/` | POST | Criar pedido de corrida |
| `/api/corridas/{id}/aceitar/` | POST | Motorista aceita corrida |
| `/api/corridas/{id}/recusar/` | POST | Motorista recusa corrida |
| `/api/corridas/{id}/concluir/` | POST | Marcar corrida como concluída |
| `/api/motoristas/verificar-assinatura/` | GET | Verificar assinatura activa |
| `/api/motoristas/proximos/` | GET | Buscar motoristas num raio |

Todos os endpoints verificam `X-Bot-Secret` header.

---

## 5. Variáveis de ambiente do bot

```bash
# Comunicação com Django
BACKEND_URL=https://motogram.app
BOT_SECRET=token-secreto-interno

# Telegram
TELEGRAM_TOKEN=1234567890:ABC...

# Redis (FSM do aiogram)
REDIS_URL=redis://...upstash.io:6379
```

---

## 6. Referência: código fonte do LibreTaxi

Para implementar funcionalidades do MotoGram, consultar o código fonte do LibreTaxi como referência:

| Funcionalidade | Ficheiro LibreTaxi (referência) |
|---|---|
| Handler /start | `handlers/start.go` |
| Fluxo passageiro | `handlers/passenger.go` |
| Fluxo motorista | `handlers/driver.go` |
| Matching geográfico | `geo/` (haversine ou PostGIS) |
| Estados da conversa | `session/` (FSM) |
| Multi-language | `locale/` (ficheiros .json) |

**Como usar:** ler o código Go para entender a lógica, depois reimplementar em Python/aiogram 3. Não copiar código Go diretamente.
