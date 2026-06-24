"""Testes do webhook Mercado Pago."""

import json
import hmac
import hashlib
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import date, timedelta

from motoristas.models import Utilizador, Motorista
from pagamentos.models import Assinatura


@override_settings(MP_WEBHOOK_SECRET="test-webhook-secret", MP_ACCESS_TOKEN="test-access-token")
class WebhookMercadoPagoTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.utilizador = Utilizador.objects.create_user(
            username="motorista1",
            password="testpass123",
            tipo="motorista",
            email="motorista@test.com",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="João Silva",
            cpf="123.456.789-00",
            data_nascimento=date(1990, 1, 1),
            telefone="92999999999",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG 160",
            ano_moto=2020,
            cor_moto="Vermelha",
            placa="ABC-1234",
        )

    def _sign(self, body, x_request_id="req-123"):
        payload = f"{x_request_id}{body}".encode()
        return hmac.new(b"test-webhook-secret", payload, hashlib.sha256).hexdigest()

    @patch("pagamentos.services.requests.get")
    def test_webhook_valido_activa_assinatura(self, mock_get):
        assinatura = Assinatura.objects.create(
            motorista=self.motorista,
            valor=69.00,
            pix_txid="tx-abc-123",
            status="pendente",
        )

        # Mock Mercado Pago API — pagamento aprovado
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "approved"}

        payload = {"data": {"id": "tx-abc-123"}, "type": "payment"}
        body = json.dumps(payload)

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=self._sign(body),
            HTTP_X_REQUEST_ID="req-123",
        )
        self.assertEqual(response.status_code, 200)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "paga")
        self.motorista.refresh_from_db()
        self.assertTrue(self.motorista.activo)

    @patch("pagamentos.services.requests.get")
    def test_webhook_pagamento_nao_aprovado_nao_activa(self, mock_get):
        assinatura = Assinatura.objects.create(
            motorista=self.motorista,
            valor=69.00,
            pix_txid="tx-rejeitado",
            status="pendente",
        )

        # Mock — pagamento rejeitado
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "rejected"}

        payload = {"data": {"id": "tx-rejeitado"}, "type": "payment"}
        body = json.dumps(payload)

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=self._sign(body),
            HTTP_X_REQUEST_ID="req-123",
        )
        self.assertEqual(response.status_code, 200)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "pendente")

    def test_webhook_txid_nao_encontrado(self):
        payload = {"data": {"id": "tx-nao-existe"}, "type": "payment"}
        body = json.dumps(payload)

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=self._sign(body),
            HTTP_X_REQUEST_ID="req-123",
        )
        self.assertEqual(response.status_code, 200)

    def test_webhook_tipo_diferente_ignorado(self):
        payload = {"data": {"id": "ignorado"}, "type": "outro"}
        body = json.dumps(payload)

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=self._sign(body),
            HTTP_X_REQUEST_ID="req-123",
        )
        self.assertEqual(response.status_code, 200)
