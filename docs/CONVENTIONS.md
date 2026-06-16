# CONVENTIONS.md — MotoGram

Convenções de código, nomenclatura e organização para o projecto MotoGram.

---

## Python / Django

### Nomenclatura

```python
# Modelos — singular, PascalCase
class Motorista(Model): ...
class Corrida(Model): ...
class Assinatura(Model): ...

# Campos — snake_case, descritivos
assinatura_ate = DateField()        # ✅
assinDate = DateField()             # ❌

# Views — sufixo View ou nome do endpoint
class CorridaCriarView(APIView): ...
class MotoristasDashboardView(APIView): ...

# URLs — kebab-case, plural para listas, singular para acções
/api/corridas/                      # lista / criar
/api/corridas/{id}/                 # detalhe
/api/corridas/{id}/aceitar/         # acção
/api/motoristas/proximos/           # query especial
```

### Organização de ficheiros

```python
# models.py — modelos + propriedades simples
@property
def assinatura_activa(self):
    return self.activo and self.assinatura_ate >= date.today()

# services.py — lógica de negócio complexa (nunca nas views)
def activar_motorista_apos_pagamento(assinatura_id: int) -> Motorista:
    ...

# serializers.py — só serialização, sem lógica de negócio
# views.py — só orquestração: valida → chama service → retorna resposta
```

### Imports

```python
# Ordem: stdlib → django → third-party → local
import os
from datetime import date, timedelta

from django.db import models
from django.utils import timezone
from rest_framework.views import APIView

import requests

from motoristas.models import Motorista
from motoristas.services import activar_motorista
```

---

## Bot Telegram (aiogram 3)

### Nomenclatura de handlers

```python
# Prefixo do fluxo + acção
async def passageiro_enviar_localizacao(message: Message): ...
async def motorista_aceitar_corrida(callback: CallbackQuery): ...
async def corrida_concluida(callback: CallbackQuery): ...
```

### Estados FSM

```python
# states.py — sempre em classes, nunca strings soltas
class PassageiroStates(StatesGroup):
    aguardando_localizacao = State()
    aguardando_destino = State()
    corrida_em_curso = State()

class MotoristaStates(StatesGroup):
    disponivel = State()
    em_corrida = State()
```

### Mensagens do bot

```python
# Sempre definir mensagens como constantes, nunca inline
# bot/messages.py
CORRIDA_ACEITE = (
    "✅ *Corrida aceite!*\n\n"
    "📍 Passageiro em: {origem}\n"
    "📞 Contacto: {telefone}\n\n"
    "Boa corrida! 🏍️"
)

# No handler:
await message.answer(
    CORRIDA_ACEITE.format(origem=corrida.origem, telefone=passageiro.telefone),
    parse_mode="Markdown"
)
```

---

## Templates HTML

### Estrutura base

```html
<!-- Sempre começar com viewport mobile -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- Classes Tailwind: mobile primeiro, depois sm: md: lg: -->
<div class="max-w-md mx-auto min-h-dvh flex flex-col">   <!-- ✅ mobile-first -->
<div class="px-8 py-6 sm:px-4">       <!-- ❌ desktop-first -->

<!-- Botões de acção — sempre full width no mobile -->
<button class="w-full sm:w-auto btn-primary">
    Pedir corrida
</button>
```

### Componentes reutilizáveis

```html
<!-- Templates Django para componentes repetidos -->
<!-- Nota: directório components/ ainda não existe — usar inline por agora -->
```

### Interactividade com Alpine.js

```html
<!-- Alpine.js para estados simples — nunca para lógica de negócio -->
<div x-data="{ aberto: false }">
    <button @click="aberto = !aberto">Ver detalhes</button>
    <div x-show="aberto">...</div>
</div>

<!-- Polling de estado da corrida -->
<div x-data="statusCorrida('{{ corrida.id }}')" x-init="iniciar()">
    <p x-text="status"></p>
</div>
```

---

## API REST

### Respostas de erro

```python
# Sempre incluir campo 'erro' com mensagem legível
return Response({'erro': 'Assinatura inactiva. Renova em motogram.app/motorista/conta'}, status=403)
return Response({'erro': 'Corrida não encontrada'}, status=404)
return Response({'erro': 'Localização inválida'}, status=400)

# Nunca expor detalhes internos
return Response({'erro': str(exception)}, status=500)  # ❌
return Response({'erro': 'Erro interno. Tenta novamente.'}, status=500)  # ✅
```

### Paginação

```python
# Sempre paginar listas que podem crescer
class HistoricoCorridasView(APIView):
    def get(self, request):
        corridas = Corrida.objects.filter(motorista__utilizador=request.user)
        paginator = PageNumberPagination()
        paginator.page_size = 20
        resultado = paginator.paginate_queryset(corridas, request)
        return paginator.get_paginated_response(CorridaSerializer(resultado, many=True).data)
```

---

## Segurança

### Autenticação

```python
# Endpoints do motorista — sempre IsAuthenticated
# Endpoints do passageiro — podem ser públicos (sem conta)
# Endpoints admin — IsAdminUser
# Webhook Mercado Pago — validação por assinatura HMAC, não por sessão
```

### Token de activação Telegram

```python
# Geração
import secrets
token = secrets.token_urlsafe(16)

# Validação
def validar_token_telegram(token: str) -> Motorista | None:
    try:
        motorista = Motorista.objects.get(
            telegram_token=token,
            telegram_token_expiry__gt=timezone.now()
        )
        # Token de uso único — apagar após validação
        motorista.telegram_token = None
        motorista.telegram_token_expiry = None
        motorista.save()
        return motorista
    except Motorista.DoesNotExist:
        return None
```

---

## Git

### Mensagens de commit

```
feat: adicionar webhook de pagamento Pix
fix: corrigir matching geográfico quando não há motoristas próximos
refactor: mover lógica de assinatura para services.py
docs: actualizar ROADMAP com Fase 2
test: adicionar testes para activação de motorista
chore: actualizar dependências Python
```

### Branches

```
main          — produção (Railway deploy automático)
develop       — integração
feat/nome     — novas funcionalidades
fix/nome      — correcções
```

---

## Variáveis de Ambiente

- Nunca commitar o ficheiro `.env`
- `.env.example` sempre actualizado com todas as variáveis (sem valores reais)
- Em produção, configurar variáveis directamente no dashboard do Railway
