"""Testes das views do motorista."""

from django.test import TestCase, Client
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista


class CadastroMotoristaTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_cadastro_page_loads(self):
        response = self.client.get("/motorista/cadastro/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro Motorista")

    def test_cadastro_sucesso(self):
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
        self.assertTrue(Utilizador.objects.filter(email="joao@test.com").exists())
        self.assertTrue(Motorista.objects.filter(cpf="123.456.789-00").exists())

    def test_cadastro_email_duplicado(self):
        Utilizador.objects.create_user(
            username="joao@test.com",
            email="joao@test.com",
            password="test123",
        )
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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-mail já registado")


class LoginMotoristaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.utilizador = Utilizador.objects.create_user(
            username="motorista@test.com",
            email="motorista@test.com",
            password="test123",
            tipo="motorista",
        )

    def test_login_page_loads(self):
        response = self.client.get("/motorista/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login Motorista")

    def test_login_sucesso(self):
        response = self.client.post("/motorista/login/", {
            "username": "motorista@test.com",
            "password": "test123",
        })
        self.assertEqual(response.status_code, 302)

    def test_login_credenciais_invalidas(self):
        response = self.client.post("/motorista/login/", {
            "username": "motorista@test.com",
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Credenciais inválidas")


class DashboardMotoristaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.utilizador = Utilizador.objects.create_user(
            username="motorista@test.com",
            email="motorista@test.com",
            password="test123",
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
        )

    def test_dashboard_requires_login(self):
        response = self.client.get("/motorista/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_logged_user(self):
        self.client.login(username="motorista@test.com", password="test123")
        response = self.client.get("/motorista/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João Silva")
