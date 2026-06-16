"""Testes dos endpoints de motoristas."""

import json
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista


@override_settings(BOT_SECRET="test-secret")
class VerificarAssinaturaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.utilizador = Utilizador.objects.create_user(
            username="motorista1",
            password="testpass123",
            tipo="motorista",
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
            activo=True,
            assinatura_ate=date.today() + timedelta(days=15),
            telegram_id=999999999,
        )

    def test_assinatura_activa(self):
        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 999999999},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["active"])

    def test_assinatura_inactiva(self):
        self.motorista.activo = False
        self.motorista.save()

        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 999999999},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["active"])
        self.assertIn("link", data)

    def test_motorista_nao_encontrado(self):
        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 000000000},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["active"])

    def test_sem_auth(self):
        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 999999999},
        )
        self.assertEqual(response.status_code, 403)

    def test_sem_telegram_id(self):
        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 400)


@override_settings(BOT_SECRET="test-secret")
class ActivarTelegramTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.utilizador = Utilizador.objects.create_user(
            username="motorista2",
            password="testpass123",
            tipo="motorista",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="Maria Santos",
            cpf="987.654.321-00",
            data_nascimento=date(1995, 5, 10),
            telefone="92988888888",
            cidade="Manaus",
            bairros=["Flores"],
            modelo_moto="Honda Biz",
            ano_moto=2021,
            cor_moto="Preta",
            placa="XYZ-5678",
            telegram_token="valid-token-123",
            telegram_token_expiry=timezone.now() + timedelta(hours=1),
        )

    def test_activar_com_token_valido(self):
        response = self.client.post(
            "/api/motoristas/activar-telegram/",
            data=json.dumps({"token": "valid-token-123", "telegram_id": 555555555}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.motorista.refresh_from_db()
        self.assertEqual(self.motorista.telegram_id, 555555555)
        self.assertIsNone(self.motorista.telegram_token)

    def test_activar_com_token_invalido(self):
        response = self.client.post(
            "/api/motoristas/activar-telegram/",
            data=json.dumps({"token": "invalid-token", "telegram_id": 555555555}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 400)

    def test_activar_com_token_expirado(self):
        self.motorista.telegram_token_expiry = timezone.now() - timedelta(hours=1)
        self.motorista.save()

        response = self.client.post(
            "/api/motoristas/activar-telegram/",
            data=json.dumps({"token": "valid-token-123", "telegram_id": 555555555}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 400)
