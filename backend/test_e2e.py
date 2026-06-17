"""Testes de ponta a ponta — fluxo completo."""

import json
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista
from corridas.models import Corrida, Oferta


@override_settings(BOT_SECRET="test-secret")
class FluxoCompletoTest(TestCase):
    """Testa o fluxo completo: cadastro → pagamento → corrida."""

    def setUp(self):
        self.client = Client()

    def test_fluxo_cadastro_motorista(self):
        """Motorista cadastra-se e vê dashboard."""
        response = self.client.post("/motorista/cadastro/", {
            "nome_completo": "João Silva",
            "cpf": "123.456.789-00",
            "data_nascimento": "1990-01-01",
            "telefone": "92999999999",
            "email": "joao@test.com",
            "cidade": "Manaus",
            "modelo_moto": "Honda CG 160",
            "ano_moto": "2020",
            "cor_moto": "Vermelha",
            "placa": "ABC-1234",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Motorista.objects.filter(cpf="123.456.789-00").exists())

    def test_fluxo_criar_corrida(self):
        """Passageiro cria corrida via API."""
        passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            telegram_id=111111111,
            tipo="passageiro",
        )

        response = self.client.post(
            "/api/corridas/",
            data='{"passageiro_telegram_id": 111111111, "origem_lat": -3.1, "origem_lon": -60.0, "valor_sugerido": 12.00}',
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Corrida.objects.filter(passageiro=passageiro).exists())

    def test_fluxo_aceitar_corrida(self):
        """Motorista aceita e passageiro escolhe — fluxo completo InDrive."""
        passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            telegram_id=111111111,
            tipo="passageiro",
        )
        utilizador_motorista = Utilizador.objects.create_user(
            username="motorista1",
            telegram_id=999999999,
            tipo="motorista",
        )
        motorista = Motorista.objects.create(
            utilizador=utilizador_motorista,
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

        corrida = Corrida.objects.create(
            passageiro=passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            valor_sugerido=12.00,
            status="aguardando",
        )

        response = self.client.post(
            f"/api/corridas/{corrida.id}/aceitar/",
            data='{"motorista_telegram_id": 999999999}',
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        oferta = Oferta.objects.get(corrida=corrida, motorista=motorista)
        self.assertEqual(oferta.tipo, "aceite")

        response = self.client.post(
            f"/api/corridas/{corrida.id}/escolher/",
            data=json.dumps({"oferta_id": oferta.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "aceite")
        self.assertEqual(corrida.motorista, motorista)
        self.assertEqual(float(corrida.valor), 12.00)

    def test_fluxo_polling_passageiro(self):
        """Passageiro faz polling e vê status."""
        passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            telegram_id=111111111,
            tipo="passageiro",
        )
        corrida = Corrida.objects.create(
            passageiro=passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            status="aguardando",
        )

        response = self.client.get(f"/api/corridas/{corrida.id}/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "aguardando")

    def test_fluxo_verificar_assinatura(self):
        """Bot verifica assinatura do motorista."""
        utilizador = Utilizador.objects.create_user(
            username="motorista1",
            telegram_id=999999999,
            tipo="motorista",
        )
        Motorista.objects.create(
            utilizador=utilizador,
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

        response = self.client.get(
            "/api/motoristas/verificar-assinatura/",
            {"telegram_id": 999999999},
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["active"])
