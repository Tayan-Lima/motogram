"""Testes do webhook Mercado Pago."""

import json
import hmac
import hashlib
from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta

from motoristas.models import Utilizador, Motorista
from pagamentos.models import Assinatura


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

    def test_webhook_valido_activa_assinatura(self):
        assinatura = Assinatura.objects.create(
            motorista=self.motorista,
            valor=69.00,
            pix_txid="tx-abc-123",
            status="pendente",
        )

        payload = {
            "data": {"id": "tx-abc-123"},
            "type": "payment",
        }

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "paga")
        self.motorista.refresh_from_db()
        self.assertTrue(self.motorista.activo)

    def test_webhook_txid_nao_encontrado(self):
        payload = {
            "data": {"id": "tx-nao-existe"},
            "type": "payment",
        }

        response = self.client.post(
            "/api/webhook/mercadopago/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
