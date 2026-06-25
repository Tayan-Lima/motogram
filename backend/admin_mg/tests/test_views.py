"""Testes para views do painel admin_mg — passageiros pendentes + confirmacao email."""

from django.test import TestCase, Client
from django.urls import reverse
from motoristas.models import Utilizador


class PassageirosPendentesTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.admin = Utilizador.objects.create_user(
            username="admin_test", email="admin@teste.com",
            password="admin123", tipo="admin",
            is_staff=True, is_superuser=True,
        )
        self.passageiro = Utilizador.objects.create_user(
            username="pass_pendente", email="pass@teste.com",
            password="pass123", tipo="passageiro",
            email_confirmado=False,
        )
        self.passageiro_ok = Utilizador.objects.create_user(
            username="pass_ok", email="pass_ok@teste.com",
            password="pass123", tipo="passageiro",
            email_confirmado=True,
        )

    def test_pendentes_lista_sem_login_redireciona(self):
        """Passageiros pendentes exige login de admin."""
        response = self.client.get(reverse("admin_mg:passageiros_pendentes"))
        self.assertEqual(response.status_code, 302)

    def test_pendentes_lista_como_passageiro_bloqueado(self):
        """Passageiro normal nao pode aceder — AdminMixin retorna 404."""
        self.client.login(username="pass_pendente", password="pass123")
        response = self.client.get(reverse("admin_mg:passageiros_pendentes"))
        self.assertEqual(response.status_code, 404)

    def test_pendentes_lista_admin_mostra_nao_confirmados(self):
        """Admin ve apenas passageiros com email_confirmado=False."""
        self.client.login(username="admin_test", password="admin123")
        response = self.client.get(reverse("admin_mg:passageiros_pendentes"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pass@teste.com")
        self.assertNotContains(response, "pass_ok@teste.com")

    def test_confirmar_email_admin(self):
        """Admin confirma email e passageiro some da lista."""
        self.client.login(username="admin_test", password="admin123")
        url = reverse("admin_mg:passageiro_detalhe", args=[self.passageiro.id])
        response = self.client.post(url, {"accao": "confirmar_email"})
        self.assertEqual(response.status_code, 302)

        self.passageiro.refresh_from_db()
        self.assertTrue(self.passageiro.email_confirmado)

        response = self.client.get(reverse("admin_mg:passageiros_pendentes"))
        self.assertNotContains(response, "pass@teste.com")

    def test_confirmar_email_passageiro(self):
        """Passageiro nao consegue confirmar o proprio email via admin — AdminMixin retorna 404."""
        self.client.login(username="pass_pendente", password="pass123")
        url = reverse("admin_mg:passageiro_detalhe", args=[self.passageiro.id])
        response = self.client.post(url, {"accao": "confirmar_email"})
        self.assertEqual(response.status_code, 404)
        self.passageiro.refresh_from_db()
        self.assertFalse(self.passageiro.email_confirmado)

    def test_pendentes_lista_vazia(self):
        """Quando todos estao confirmados, pagina mostra vazio."""
        self.passageiro.email_confirmado = True
        self.passageiro.save()
        self.client.login(username="admin_test", password="admin123")
        response = self.client.get(reverse("admin_mg:passageiros_pendentes"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum passageiro pendente")
