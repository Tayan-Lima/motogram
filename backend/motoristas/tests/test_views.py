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


class ToggleOnlineViewTest(TestCase):
    """Testes do ToggleOnlineView — GET e POST."""

    def setUp(self):
        self.client = Client()
        self.utilizador = Utilizador.objects.create_user(
            username="toggletest@gmail.com",
            password="testpass123",
            tipo="motorista",
            email="toggletest@gmail.com",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="Toggle Silva",
            cpf="111.222.333-44",
            data_nascimento=date(1990, 1, 1),
            telefone="92911111111",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG",
            ano_moto=2022,
            cor_moto="Azul",
            placa="TOG-1111",
            activo=False,
        )
        self.client.login(username="toggletest@gmail.com", password="testpass123")

    def test_get_retorna_estado_actual(self):
        resp = self.client.get("/api/motoristas/toggle-online/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["activo"])

    def test_post_activa_motorista(self):
        resp = self.client.post(
            "/api/motoristas/toggle-online/",
            data=json.dumps({"activo": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["activo"])
        self.motorista.refresh_from_db()
        self.assertTrue(self.motorista.activo)

    def test_post_desactiva_motorista(self):
        self.motorista.activo = True
        self.motorista.save()

        resp = self.client.post(
            "/api/motoristas/toggle-online/",
            data=json.dumps({"activo": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["activo"])
        self.motorista.refresh_from_db()
        self.assertFalse(self.motorista.activo)

    def test_post_toggle_sem_body(self):
        self.motorista.activo = False
        self.motorista.save()

        resp = self.client.post("/api/motoristas/toggle-online/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["activo"])  # toggled
        self.motorista.refresh_from_db()
        self.assertTrue(self.motorista.activo)

    def test_get_sem_login_redirects(self):
        self.client.logout()
        resp = self.client.get("/api/motoristas/toggle-online/")
        self.assertEqual(resp.status_code, 302)


@override_settings(BOT_SECRET="test-secret")
class BotAtualizarLocalizacaoViewTest(TestCase):
    """Testes do endpoint bot de atualização de localização."""

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.utilizador = Utilizador.objects.create_user(
            username="botloctest@gmail.com",
            password="testpass123",
            tipo="motorista",
            email="botloctest@gmail.com",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="BotLoc Silva",
            cpf="777.888.999-00",
            data_nascimento=date(1990, 1, 1),
            telefone="92933333333",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG",
            ano_moto=2022,
            cor_moto="Azul",
            placa="BLT-1111",
            telegram_id=123456789,
            activo=True,
        )

    def test_atualizar_localizacao_bot_sucesso(self):
        resp = self.client.post(
            "/api/motoristas/atualizar-localizacao/",
            data=json.dumps({
                "telegram_id": 123456789,
                "latitude": -3.1,
                "longitude": -60.0,
            }),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.motorista.refresh_from_db()
        self.assertIsNotNone(self.motorista.ultima_localizacao_em)

    def test_atualizar_localizacao_bot_sem_auth(self):
        resp = self.client.post(
            "/api/motoristas/atualizar-localizacao/",
            data=json.dumps({
                "telegram_id": 123456789,
                "latitude": -3.1,
                "longitude": -60.0,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_atualizar_localizacao_bot_motorista_nao_encontrado(self):
        resp = self.client.post(
            "/api/motoristas/atualizar-localizacao/",
            data=json.dumps({
                "telegram_id": 999999999,
                "latitude": -3.1,
                "longitude": -60.0,
            }),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 404)

    def test_atualizar_localizacao_bot_sem_campos(self):
        resp = self.client.post(
            "/api/motoristas/atualizar-localizacao/",
            data=json.dumps({"telegram_id": 123456789}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 400)


@override_settings(BOT_SECRET="test-secret")
class VerificarAssinaturaLocalizacaoTest(TestCase):
    """Testa que VerificarAssinaturaView retorna info de localização."""

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.utilizador = Utilizador.objects.create_user(
            username="verloc@gmail.com",
            password="testpass123",
            tipo="motorista",
            email="verloc@gmail.com",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="VerLoc Silva",
            cpf="123.000.000-01",
            data_nascimento=date(1990, 1, 1),
            telefone="92999999990",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG",
            ano_moto=2022,
            cor_moto="Preta",
            placa="VER-1111",
            activo=True,
            assinatura_ate=date.today() + timedelta(days=15),
            telegram_id=111111111,
        )

    def test_localizacao_desatualizada_sem_nunca_actualizar(self):
        resp = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 111111111},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["active"])
        self.assertTrue(data["localizacao_desatualizada"])
        self.assertEqual(data["nome"], "VerLoc Silva")

    def test_localizacao_fresca(self):
        self.motorista.ultima_localizacao_em = timezone.now() - timedelta(minutes=10)
        self.motorista.save()

        resp = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 111111111},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["active"])
        self.assertFalse(data["localizacao_desatualizada"])

    def test_localizacao_desatualizada_mais_de_30min(self):
        self.motorista.ultima_localizacao_em = timezone.now() - timedelta(hours=1)
        self.motorista.save()

        resp = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 111111111},
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["active"])
        self.assertTrue(data["localizacao_desatualizada"])


@override_settings(BOT_SECRET="test-secret")
class BotToggleOnlineViewTest(TestCase):
    """Testes do endpoint toggle-online-bot (bot → backend)."""

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.utilizador = Utilizador.objects.create_user(
            username="bottoggle@gmail.com",
            password="testpass123",
            tipo="motorista",
            email="bottoggle@gmail.com",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo="Bot Toggle",
            cpf="321.654.987-00",
            data_nascimento=date(1990, 1, 1),
            telefone="92955555555",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG",
            ano_moto=2022,
            cor_moto="Verde",
            placa="BTG-1111",
            activo=False,
            telegram_id=777777777,
        )

    def _post(self, telegram_id, activo):
        return self.client.post(
            "/api/motoristas/toggle-online-bot/",
            data=json.dumps({"telegram_id": telegram_id, "activo": activo}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )

    def test_activa_motorista(self):
        resp = self._post(777777777, True)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["activo"])
        self.motorista.refresh_from_db()
        self.assertTrue(self.motorista.activo)

    def test_desactiva_motorista(self):
        self.motorista.activo = True
        self.motorista.save()

        resp = self._post(777777777, False)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["activo"])
        self.motorista.refresh_from_db()
        self.assertFalse(self.motorista.activo)

    def test_sem_auth(self):
        resp = self.client.post(
            "/api/motoristas/toggle-online-bot/",
            data=json.dumps({"telegram_id": 777777777, "activo": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_motorista_nao_encontrado(self):
        resp = self._post(999999999, True)
        self.assertEqual(resp.status_code, 404)

    def test_sem_telegram_id(self):
        resp = self.client.post(
            "/api/motoristas/toggle-online-bot/",
            data=json.dumps({"activo": True}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 400)

    def test_json_invalido(self):
        resp = self.client.post(
            "/api/motoristas/toggle-online-bot/",
            data="not json",
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(resp.status_code, 400)
