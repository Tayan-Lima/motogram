"""Testes de ponta a ponta — fluxo completo."""

import json
import re
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista
from corridas.models import Corrida, Oferta
from pagamentos.models import Assinatura


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
            "password": "teste123",
            "password_confirm": "teste123",
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

    @patch("corridas.views._notificar_resultado_ofertas")
    @patch("corridas.views.notificar_motoristas_proximos")
    def test_fluxo_passageiro_completo(self, mock_notificar, mock_resultado):
        """Passageiro registra-se, pede corrida, escolhe motorista e acompanha."""
        response = self.client.post("/passageiro/cadastro/", {
            "telefone": "(92) 99999-8888",
            "nome": "Maria Silva",
            "email": "maria@test.com",
            "password": "teste123",
            "password_confirm": "teste123",
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post("/passageiro/login/", {
            "username": "maria@test.com",
            "password": "teste123",
        })
        self.assertEqual(response.status_code, 302)

        Utilizador.objects.filter(email="maria@test.com").update(email_confirmado=True)

        response = self.client.post(
            "/api/corridas/web/",
            data=json.dumps({
                "origem_lat": -3.1,
                "origem_lon": -60.0,
                "destino_lat": -3.11,
                "destino_lon": -60.01,
                "destino_texto": "Centro",
                "valor_sugerido": "12.00",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        corrida = Corrida.objects.get(id=response.json()["id"])
        self.assertEqual(corrida.status, "aguardando")

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

        response = self.client.post(
            f"/api/corridas/{corrida.id}/aceitar/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        oferta = Oferta.objects.get(corrida=corrida, motorista=motorista)

        response = self.client.post(
            f"/api/corridas/{corrida.id}/escolher/",
            data=json.dumps({"oferta_id": oferta.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "aceite")
        self.assertEqual(corrida.motorista, motorista)

        response = self.client.get(f"/api/corridas/{corrida.id}/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "aceite")
        self.assertIn("motorista", data)
        self.assertEqual(data["motorista"]["nome"], "João Silva")

    @patch("corridas.views._notificar_resultado_ofertas")
    @patch("corridas.views.notificar_motoristas_proximos")
    def test_fluxo_motorista_completo(self, mock_notificar, mock_resultado):
        """Motorista: cadastro → assinatura → pagamento → Telegram → corrida → conclusão."""
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
            "password": "teste123",
            "password_confirm": "teste123",
        })
        self.assertEqual(response.status_code, 302)
        motorista = Motorista.objects.get(cpf="123.456.789-00")

        response = self.client.post("/motorista/login/", {
            "username": "joao@test.com",
            "password": "teste123",
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post("/api/assinaturas/criar/")
        self.assertEqual(response.status_code, 201)
        assinatura = Assinatura.objects.get(motorista=motorista)
        self.assertEqual(assinatura.status, "pendente")

        with self.settings(MP_WEBHOOK_SECRET=""):
            response = self.client.post(
                "/api/webhook/mercadopago/",
                data=json.dumps({
                    "data": {"id": assinatura.pix_txid},
                    "type": "payment",
                }),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        motorista.refresh_from_db()
        assinatura.refresh_from_db()
        self.assertTrue(motorista.activo)
        self.assertEqual(assinatura.status, "paga")

        motorista.status_cadastro = "aprovado"
        motorista.save()

        response = self.client.post("/motorista/gerar-link-telegram/")
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]

        response = self.client.post(
            "/api/motoristas/activar-telegram/",
            data=json.dumps({"token": token, "telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        motorista.refresh_from_db()
        self.assertEqual(motorista.telegram_id, 999999999)

        response = self.client.post(
            "/api/motoristas/toggle-online/",
            data=json.dumps({"activo": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["activo"])

        passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            telegram_id=111111111,
            tipo="passageiro",
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
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        oferta = Oferta.objects.get(corrida=corrida, motorista=motorista)

        response = self.client.post(
            f"/api/corridas/{corrida.id}/escolher/",
            data=json.dumps({"oferta_id": oferta.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "aceite")

        response = self.client.post(
            f"/api/corridas/{corrida.id}/concluir/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "concluida")

    def test_fluxo_motorista_assinatura_expirada(self):
        """Motorista com assinatura expirada não pode aceitar corridas."""
        utilizador_motorista = Utilizador.objects.create_user(
            username="motorista1",
            telegram_id=999999999,
            tipo="motorista",
        )
        Motorista.objects.create(
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
            assinatura_ate=date.today() - timedelta(days=1),
            telegram_id=999999999,
        )

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

        response = self.client.post(
            f"/api/corridas/{corrida.id}/aceitar/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn("erro", data)
        self.assertIn("Assinatura", data["erro"])

    def test_fluxo_motorista_recusar_corrida(self):
        """Motorista recusa corrida e ela continua disponível."""
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

        response = self.client.post(
            f"/api/corridas/{corrida.id}/recusar/",
            data=json.dumps({"motorista_telegram_id": 999999999}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "aguardando")

    @patch("corridas.views._notificar_resultado_ofertas")
    def test_fluxo_motorista_contra_oferta(self, mock_resultado):
        """Motorista faz contra-oferta e passageiro aceita."""
        passageiro = Utilizador.objects.create_user(
            username="passageiro1",
            telegram_id=111111111,
            tipo="passageiro",
        )
        corrida = Corrida.objects.create(
            passageiro=passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
            valor_sugerido=12.00,
            status="aguardando",
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

        response = self.client.post(
            f"/api/corridas/{corrida.id}/ofertar/",
            data=json.dumps({"motorista_telegram_id": 999999999, "valor": "15.00"}),
            content_type="application/json",
            HTTP_X_BOT_SECRET="test-secret",
        )
        self.assertEqual(response.status_code, 200)
        oferta = Oferta.objects.get(corrida=corrida, motorista=motorista)
        self.assertEqual(oferta.tipo, "contra_oferta")
        self.assertEqual(float(oferta.valor), 15.00)

        response = self.client.post(
            f"/api/corridas/{corrida.id}/escolher/",
            data=json.dumps({"oferta_id": oferta.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, "aceite")
        self.assertEqual(corrida.motorista, motorista)
        self.assertEqual(float(corrida.valor), 15.00)

    def test_fluxo_motorista_online_offline(self):
        """Motorista alterna entre online e offline."""
        response = self.client.post("/motorista/cadastro/", {
            "nome_completo": "João Silva",
            "cpf": "123.456.789-01",
            "data_nascimento": "1990-01-01",
            "telefone": "92999999998",
            "email": "joao2@test.com",
            "cidade": "Manaus",
            "modelo_moto": "Honda CG 160",
            "ano_moto": "2020",
            "cor_moto": "Vermelha",
            "placa": "ABC-1235",
            "password": "teste123",
            "password_confirm": "teste123",
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post("/motorista/login/", {
            "username": "joao2@test.com",
            "password": "teste123",
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            "/api/motoristas/toggle-online/",
            data=json.dumps({"activo": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["activo"])

        response = self.client.post(
            "/api/motoristas/toggle-online/",
            data=json.dumps({"activo": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["activo"])

        response = self.client.post(
            "/api/motoristas/toggle-online/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["activo"])

    @patch("corridas.services.notificar_motorista_telegram")
    def test_fluxo_recuperar_senha_passageiro(self, mock_notificar):
        """Passageiro recupera senha e consegue fazer login com nova senha."""
        utilizador = Utilizador.objects.create_user(
            username="maria@test.com",
            email="maria@test.com",
            password="senha_antiga",
            tipo="passageiro",
            telegram_id=111111111,
        )

        response = self.client.post("/passageiro/recuperar-senha/", {
            "email": "maria@test.com",
        })
        self.assertEqual(response.status_code, 200)

        utilizador.refresh_from_db()
        self.assertFalse(utilizador.check_password("senha_antiga"))

        args, _ = mock_notificar.call_args
        mensagem = args[1]
        match = re.search(r"A tua nova senha é: `([^`]+)`", mensagem)
        self.assertIsNotNone(match)
        nova_senha = match.group(1)

        response = self.client.post("/passageiro/login/", {
            "username": "maria@test.com",
            "password": nova_senha,
        })
        self.assertEqual(response.status_code, 302)

    @patch("corridas.services.notificar_motorista_telegram")
    def test_fluxo_recuperar_senha_motorista(self, mock_notificar):
        """Motorista recupera senha e consegue fazer login com nova senha."""
        utilizador = Utilizador.objects.create_user(
            username="joao3@test.com",
            email="joao3@test.com",
            password="senha_antiga",
            tipo="motorista",
        )
        Motorista.objects.create(
            utilizador=utilizador,
            nome_completo="João Silva",
            cpf="123.456.789-02",
            data_nascimento=date(1990, 1, 1),
            telefone="92999999997",
            cidade="Manaus",
            bairros=["Centro"],
            modelo_moto="Honda CG 160",
            ano_moto=2020,
            cor_moto="Vermelha",
            placa="ABC-1236",
            telegram_id=999999998,
        )

        response = self.client.post("/motorista/recuperar-senha/", {
            "email": "joao3@test.com",
        })
        self.assertEqual(response.status_code, 200)

        utilizador.refresh_from_db()
        self.assertFalse(utilizador.check_password("senha_antiga"))

        args, _ = mock_notificar.call_args
        mensagem = args[1]
        match = re.search(r"A tua nova senha é: `([^`]+)`", mensagem)
        self.assertIsNotNone(match)
        nova_senha = match.group(1)

        response = self.client.post("/motorista/login/", {
            "username": "joao3@test.com",
            "password": nova_senha,
        })
        self.assertEqual(response.status_code, 302)
