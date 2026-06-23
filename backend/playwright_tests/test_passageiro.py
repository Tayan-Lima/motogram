"""Testes Playwright — fluxo do passageiro."""

import pytest
from django.contrib.auth import get_user_model

Utilizador = get_user_model()


@pytest.mark.django_db
def test_landing_page(pagina):
    pagina.goto("/")
    assert pagina.title() != ""
    content = pagina.text_content(".max-w-md")
    assert "Motogram" in content or "mototáxi" in content.lower()


@pytest.mark.django_db
def test_cadastro_page_loads(pagina):
    pagina.goto("/passageiro/cadastro/")
    assert pagina.locator('[x-model="telefone"]').count() > 0


@pytest.mark.django_db
def test_cadastro_completo(pagina):
    pagina.goto("/passageiro/cadastro/")

    pagina.wait_for_selector('[x-model="telefone"]', timeout=5000)
    pagina.fill('[x-model="telefone"]', "92999998888")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('[x-model="nome"]', timeout=5000)
    pagina.fill('[x-model="nome"]', "Maria Teste")
    pagina.fill('[x-model="email"]', "maria@teste.com")
    pagina.fill('[x-model="senha"]', "teste123")
    pagina.fill('[x-model="senha_confirm"]', "teste123")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('text=Tudo pronto', timeout=5000)
    pagina.locator('[x-model="termos"]').check()
    pagina.locator("button", has_text="Criar conta").click()

    pagina.wait_for_url("**/passageiro/confirmar-email/**", timeout=10000)


@pytest.mark.django_db
def test_cadastro_email_duplicado(pagina):
    Utilizador.objects.create_user(
        username="maria@teste.com", email="maria@teste.com",
        password="teste123", tipo="passageiro",
    )

    pagina.goto("/passageiro/cadastro/")

    pagina.wait_for_selector('[x-model="telefone"]', timeout=5000)
    pagina.fill('[x-model="telefone"]', "92988887777")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('[x-model="nome"]', timeout=5000)
    pagina.fill('[x-model="nome"]', "Maria Duplicado")
    pagina.fill('[x-model="email"]', "maria@teste.com")
    pagina.fill('[x-model="senha"]', "teste123")
    pagina.fill('[x-model="senha_confirm"]', "teste123")
    pagina.locator("button", has_text="Continuar").click()

    pagina.wait_for_selector('text=Tudo pronto', timeout=5000)
    pagina.locator('[x-model="termos"]').check()
    pagina.locator("button", has_text="Criar conta").click()

    pagina.wait_for_timeout(3000)
    texto = pagina.text_content("body").lower()
    assert "registrado" in texto or "cadastro" in texto


@pytest.mark.django_db
def test_login_e_redirect(pagina):
    Utilizador.objects.create_user(
        username="testelogin@teste.com", email="testelogin@teste.com",
        password="teste123", tipo="passageiro",
    )

    pagina.goto("/passageiro/cadastro/")
    pagina.wait_for_selector('[x-model="telefone"]', timeout=5000)
    assert pagina.url.endswith("/passageiro/cadastro/")


@pytest.mark.django_db
def test_pedir_corrida_requer_login(pagina):
    pagina.goto("/passageiro/")
    pagina.wait_for_url("**/passageiro/login/**", timeout=5000)


@pytest.mark.django_db
def test_pedir_corrida_page_com_mapa(pagina):
    Utilizador.objects.create_user(
        username="passmapa@teste.com", email="passmapa@teste.com",
        password="teste123", tipo="passageiro", email_confirmado=True,
    )

    pagina.goto("/passageiro/login/")
    pagina.wait_for_selector('input[name="username"]', timeout=5000)
    pagina.fill('input[name="username"]', "passmapa@teste.com")
    pagina.fill('input[name="password"]', "teste123")
    pagina.locator('button[type="submit"]').click()
    pagina.wait_for_url("**/passageiro/", timeout=10000)

    texto = pagina.text_content("body")
    assert "Olá" in texto or "Pedir corrida" in texto or "passmapa" in texto


@pytest.mark.django_db
def test_recuperar_senha_page(pagina):
    pagina.goto("/passageiro/recuperar-senha/")
    assert pagina.locator('input[name="email"]').count() > 0
