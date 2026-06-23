# TESTING.md — Motogram GO

## Filosofia de Testes

Para um projecto em fase de validação com OpenCode/VibeCoding, o foco é em testes que protegem lógica de negócio crítica — não cobertura de 100%.

**Prioridade:**
1. Lógica de assinatura (bloquear/activar motorista)
2. Webhook de pagamento Pix
3. Matching geográfico
4. Geração e validação de token Telegram

---

## Estrutura de Testes

```
backend/
├── corridas/
│   └── tests/
│       ├── test_models.py      (4 testes — Corrida lifecycle)
│       └── test_views.py       (8 testes — endpoints + Oferta/InDrive)
├── motoristas/
│   └── tests/
│       ├── test_models.py      (9 testes — assinatura, Utilizador)
│       ├── test_services.py    (7 testes — token Telegram, activação)
│       ├── test_site.py        (8 testes — cadastro, login, dashboard)
│       └── test_views.py       (9 testes — verificar assinatura, activar Telegram)
├── pagamentos/
│   └── tests/
│       └── test_webhook.py     (2 testes — webhook Mercado Pago)
├── site_publico/
│   └── tests/
│       ├── test_views.py       (8 testes — landing, pedir corrida, cadastro)
│       └── test_map.py         (12 testes — geocoding HERE + fallback + cache + auth)
└── test_e2e.py                 (5 testes — fluxos completos)
```

**Total: 82 testes Django, 0 falhas** (126 total incluindo Playwright + bot)

**Nota (2026-06-23):** Testes de cadastro agora exigem os campos
`password` e `password_confirm` nos POSTs (mín. 6 caracteres). Ciclo de vida completo implementado — ver `docs/CHECKLIST_TESTES_MANUAIS.md` para testes manuais.

---

## Testes Críticos (Obrigatórios no MVP)

### 1. Assinatura do Motorista

```python
# motoristas/tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Motorista

class MotoristaAssinaturaTest(TestCase):

    def setUp(self):
        self.motorista = Motorista.objects.create(...)

    def test_assinatura_activa_quando_dentro_do_prazo(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.assertTrue(self.motorista.assinatura_activa)

    def test_assinatura_inactiva_quando_vencida(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() - timedelta(days=1)
        self.assertFalse(self.motorista.assinatura_activa)

    def test_assinatura_inactiva_quando_activo_false(self):
        self.motorista.activo = False
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.assertFalse(self.motorista.assinatura_activa)
```

### 2. Activação via Token Telegram

```python
# motoristas/tests/test_services.py
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from motoristas.services import validar_token_telegram

class TokenTelegramTest(TestCase):

    def test_token_valido_vincula_motorista(self):
        motorista = criar_motorista_com_token("abc123", expiry=timezone.now() + timedelta(hours=1))
        resultado = validar_token_telegram("abc123")
        self.assertEqual(resultado, motorista)

    def test_token_expirado_retorna_none(self):
        criar_motorista_com_token("abc123", expiry=timezone.now() - timedelta(hours=1))
        resultado = validar_token_telegram("abc123")
        self.assertIsNone(resultado)

    def test_token_invalido_retorna_none(self):
        resultado = validar_token_telegram("nao_existe")
        self.assertIsNone(resultado)

    def test_token_apagado_apos_uso(self):
        motorista = criar_motorista_com_token("abc123", expiry=timezone.now() + timedelta(hours=1))
        validar_token_telegram("abc123")
        motorista.refresh_from_db()
        self.assertIsNone(motorista.telegram_token)
        # Segunda tentativa com o mesmo token falha
        self.assertIsNone(validar_token_telegram("abc123"))
```

### 3. Webhook Pix

```python
# pagamentos/tests/test_webhook.py
from django.test import TestCase, Client
from unittest.mock import patch
import json, hmac, hashlib

class WebhookMercadoPagoTest(TestCase):

    def test_webhook_valido_activa_assinatura(self):
        assinatura = criar_assinatura_pendente()
        payload = {"data": {"id": assinatura.pix_txid}, "type": "payment"}
        assinatura_hmac = gerar_assinatura_hmac(payload)

        response = self.client.post(
            '/api/webhook/mercadopago/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_SIGNATURE=assinatura_hmac
        )

        self.assertEqual(response.status_code, 200)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, 'paga')
        self.assertTrue(assinatura.motorista.activo)

    def test_webhook_assinatura_invalida_rejeitado(self):
        response = self.client.post(
            '/api/webhook/mercadopago/',
            data='{}',
            content_type='application/json',
            HTTP_X_SIGNATURE='assinatura_errada'
        )
        self.assertEqual(response.status_code, 403)
```

### 4. Acesso Bloqueado sem Assinatura

```python
# corridas/tests/test_views.py
from rest_framework.test import APITestCase
from rest_framework import status

class CorridaAceitarTest(APITestCase):

    def test_motorista_sem_assinatura_nao_pode_aceitar(self):
        motorista = criar_motorista_sem_assinatura()
        corrida = criar_corrida_aguardando()
        self.client.force_authenticate(user=motorista.utilizador)

        response = self.client.post(f'/api/corridas/{corrida.id}/aceitar/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('erro', response.data)
        self.assertIn('assinatura', response.data['erro'].lower())

    def test_motorista_com_assinatura_activa_pode_aceitar(self):
        motorista = criar_motorista_com_assinatura_activa()
        corrida = criar_corrida_aguardando()
        self.client.force_authenticate(user=motorista.utilizador)

        response = self.client.post(f'/api/corridas/{corrida.id}/aceitar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, 'aceite')
```

---

## Correr Testes

```bash
# Todos os testes
cd backend
python manage.py test

# App específica
python manage.py test motoristas

# Teste específico
python manage.py test motoristas.tests.test_services.TokenTelegramTest

# Com verbose
python manage.py test --verbosity=2

# Com cobertura (instalar: pip install coverage)
coverage run manage.py test
coverage report --include="*/motoristas/*,*/corridas/*,*/pagamentos/*"
```

---

## Testes Manuais — Checklist de Deploy

Antes de cada deploy em produção, verificar manualmente:

### Bot Telegram
- [ ] `/start` responde em menos de 3 segundos
- [ ] Passageiro consegue enviar localização e receber confirmação
- [ ] Motorista activo recebe notificação de nova corrida
- [ ] Motorista inactivo recebe mensagem com link de renovação
- [ ] Aceitar corrida actualiza estado no site do passageiro

### Site — Motorista
- [ ] Cadastro completo com upload de foto CNH
- [ ] QR Code Pix gerado correctamente
- [ ] Após pagamento, link Telegram aparece na página de conta
- [ ] Link Telegram funciona e vincula a conta
- [ ] Dashboard mostra ganhos correctamente
- [ ] Renovação de assinatura funciona

### Site — Passageiro
- [ ] Pedido de corrida via mapa funciona
- [ ] Estado da corrida actualiza (polling)
- [ ] Dados do motorista aparecem após aceitação

### Admin
- [ ] Listagem de motoristas carrega
- [ ] Aprovar/bloquear motorista funciona
- [ ] Cron job de vencimento funciona (testar manualmente com data no passado)
