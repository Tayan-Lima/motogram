"""Testes das views do site público."""

from django.test import TestCase, Client
from motoristas.models import Utilizador


class LandingPageTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_landing_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MotoGram")

    def test_landing_page_contains_cta(self):
        response = self.client.get("/")
        self.assertContains(response, "Pedir corrida")


class PedirCorridaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.passageiro = Utilizador.objects.create_user(
            username="passageiro_test",
            password="test123",
            tipo="passageiro",
        )

    def test_pedir_page_requer_login(self):
        response = self.client.get("/passageiro/")
        self.assertEqual(response.status_code, 302)

    def test_pedir_page_loads_logado(self):
        self.client.login(username="passageiro_test", password="test123")
        response = self.client.get("/passageiro/")
        self.assertEqual(response.status_code, 200)

    def test_pedir_page_contains_map_placeholder(self):
        self.client.login(username="passageiro_test", password="test123")
        response = self.client.get("/passageiro/")
        self.assertContains(response, "mapa")


class CadastroPassageiroTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_cadastro_page_loads(self):
        response = self.client.get("/passageiro/cadastro/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criar conta")

    def test_cadastro_sucesso(self):
        response = self.client.post("/passageiro/cadastro/", {
            "telefone": "(92) 9 9999-8888",
            "nome": "Maria Silva",
            "email": "maria@test.com",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Utilizador.objects.filter(email="maria@test.com", tipo="passageiro").exists()
        )

    def test_cadastro_sem_telefone(self):
        response = self.client.post("/passageiro/cadastro/", {
            "nome": "Sem Telefone",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telefone")

    def test_login_passageiro(self):
        Utilizador.objects.create_user(
            username="passageiro_login",
            password="test123",
            tipo="passageiro",
        )
        response = self.client.post("/passageiro/login/", {
            "username": "passageiro_login",
            "password": "test123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/passageiro/perfil/")

    def test_login_credenciais_invalidas(self):
        response = self.client.post("/passageiro/login/", {
            "username": "inexistente",
            "password": "errada",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Credenciais")
