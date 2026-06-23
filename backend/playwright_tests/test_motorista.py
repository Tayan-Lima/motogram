"""Testes Playwright — fluxo do motorista."""

import os
import pytest
from django.contrib.auth import get_user_model
from datetime import date

Utilizador = get_user_model()


@pytest.mark.django_db
def test_cadastro_page_loads(pagina):
    pagina.goto("/motorista/cadastro/")
    assert pagina.locator('text=Dados pessoais').count() > 0


@pytest.mark.django_db
def test_cadastro_passo_1_para_2(pagina):
    pagina.goto("/motorista/cadastro/")

    pagina.wait_for_selector('input[name="nome_completo"]', timeout=5000)
    pagina.fill('input[name="nome_completo"]', "Pedro Motora")
    pagina.fill('input[name="cpf"]', "987.654.321-00")
    pagina.fill('input[name="data_nascimento"]', "1992-05-15")
    pagina.fill('input[name="telefone"]', "92987654321")
    pagina.fill('input[name="email"]', "pedro@teste.com")
    pagina.fill('input[name="cidade"]', "Manaus")
    pagina.fill('input[name="password"]', "teste123")
    pagina.fill('input[name="password_confirm"]', "teste123")

    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('input[name="modelo_moto"]', timeout=5000)
    assert pagina.locator('input[name="modelo_moto"]').is_visible()


@pytest.mark.django_db
def test_cadastro_completo(pagina):
    pagina.goto("/motorista/cadastro/")

    pagina.wait_for_selector('input[name="nome_completo"]', timeout=5000)
    pagina.fill('input[name="nome_completo"]', "Carlos Moto")
    pagina.fill('input[name="cpf"]', "111.222.333-44")
    pagina.fill('input[name="data_nascimento"]', "1990-01-01")
    pagina.fill('input[name="telefone"]', "92911112222")
    pagina.fill('input[name="email"]', "carlos@teste.com")
    pagina.fill('input[name="cidade"]', "Manaus")
    pagina.fill('input[name="password"]', "teste123")
    pagina.fill('input[name="password_confirm"]', "teste123")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('input[name="modelo_moto"]', timeout=5000)
    pagina.fill('input[name="modelo_moto"]', "Honda CG 160")
    pagina.fill('input[name="ano_moto"]', "2022")
    pagina.fill('input[name="cor_moto"]', "Preta")
    pagina.fill('input[name="placa"]', "XYZ-9999")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('input[name="cnh_frente"]', state="attached", timeout=5000)

    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "motogram-go-logo.png")
    pagina.set_input_files('input[name="cnh_frente"]', caminho)
    pagina.set_input_files('input[name="cnh_verso"]', caminho)
    pagina.set_input_files('input[name="antecedentes"]', caminho)
    pagina.set_input_files('input[name="foto_rosto"]', caminho)

    pagina.locator("button", has_text="Enviar cadastro").click()

    pagina.wait_for_url("**/motorista/dashboard/**", timeout=15000)


@pytest.mark.django_db
def test_login_motorista(pagina):
    from motoristas.models import Motorista
    user = Utilizador.objects.create_user(
        username="motologin@teste.com", email="motologin@teste.com",
        password="teste123", tipo="motorista",
    )
    Motorista.objects.create(
        utilizador=user, nome_completo="João Login", cpf="555.666.777-88",
        data_nascimento=date(1990, 1, 1), telefone="92955556666",
        cidade="Manaus", modelo_moto="Honda", ano_moto=2020,
        cor_moto="Vermelha", placa="ABC-1234", status_cadastro="aprovado",
    )

    pagina.goto("/motorista/login/")
    pagina.wait_for_selector('input[name="username"]', timeout=5000)
    pagina.fill('input[name="username"]', "motologin@teste.com")
    pagina.fill('input[name="password"]', "teste123")
    pagina.locator('button[type="submit"]').click()
    pagina.wait_for_url("**/motorista/dashboard/**", timeout=10000)

    assert "Dashboard" in pagina.text_content("body") or "Ganhos" in pagina.text_content("body")


@pytest.mark.django_db
def test_dashboard_requer_login(pagina):
    pagina.goto("/motorista/dashboard/")
    pagina.wait_for_url("**/motorista/login/**", timeout=5000)


@pytest.mark.django_db
def test_recuperar_senha_page(pagina):
    pagina.goto("/motorista/recuperar-senha/")
    assert pagina.locator('input[name="email"]').count() > 0
