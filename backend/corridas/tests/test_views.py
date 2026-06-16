"""Testes dos endpoints de corridas."""

import json
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista
from corridas.models import Corrida


@override_settings(BOT_SECRET="test-secret")
class CorridaEndpointsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.bot_secret = "test-secret"

        self.passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            password="testpass123",
            tipo="passageiro",
            telegram_id=111111111,
        )

        self.utilizador_motorista = Utilizador.objects.create_user(
            username="motorista1",
            password="testpass123",
            tipo="motorista",
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador_motorista,
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
            status_cadastro="aprovado",
            activo=True,
            assinatura_ate=date.today() + timedelta(days=15),
            telegram_id=999999999,
        )

    def test_criar_corrida(self):
        response = self.client.post(
            "/api/corridas/",
            data=json.dumps({
                "passageiro_telegram_id": 111111111,
                "origem_lat": -3.1,
                "origem_lon": -60.0,
            }),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "aguardando")

    def test_criar_corrida_sem_auth(self):
        response = self.client.post(
            "/api/corridas/",
            data=json.dumps({
                "passageiro_telegram_id": 111111111,
                "origem_lat": -3.1,
                "origem_lon": -60.0,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_aceitar_corrida(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            status="aguardando",
        )

        response = self.client.post(
            f"/api/corridas/{corrida.id}/aceitar/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "aceite")

    def test_aceitar_corrida_sem_assinatura(self):
        self.motorista.activo = False
        self.motorista.save()

        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            status="aguardando",
        )

        response = self.client.post(
            f"/api/corridas/{corrida.id}/aceitar/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET=self.bot_secret,
        )
        self.assertEqual(response.status_code, 403)

    def test_corrida_status_aguardando(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            status="aguardando",
        )

        response = self.client.get(f"/api/corridas/{corrida.id}/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "aguardando")

    def test_corrida_status_aceite(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            motorista=self.motorista,
            origem_lat=-3.1,
            origem_lon=-60.0,
            status="aceite",
        )

        response = self.client.get(f"/api/corridas/{corrida.id}/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "aceite")
        self.assertIn("motorista", data)
