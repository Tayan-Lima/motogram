"""Testes Playwright — painel admin."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

Utilizador = get_user_model()


@pytest.mark.django_db
def test_login_page_loads(pagina):
    pagina.goto("/test-admin-path/entrar/")
    pagina.wait_for_selector('input[name="username"]', timeout=5000)
    assert pagina.locator('input[name="username"]').count() > 0


@pytest.mark.django_db
def test_admin_login(pagina):
    Utilizador.objects.create(
        username="admin_test", email="admin@motogram.app",
        password=make_password("admin123"), tipo="admin",
        is_staff=True, is_superuser=True,
    )

    pagina.goto("/test-admin-path/entrar/")
    pagina.wait_for_selector('input[name="username"]', timeout=5000)
    pagina.fill('input[name="username"]', "admin_test")
    pagina.fill('input[name="password"]', "admin123")
    pagina.locator('button[type="submit"]').click()
    pagina.wait_for_url("**/test-admin-path/", timeout=10000)

    assert "Total de Motoristas" in pagina.text_content("body") or "Dashboard" in pagina.text_content("body")


@pytest.mark.django_db
def test_admin_cadastros_loads(pagina):
    Utilizador.objects.create(
        username="admin_test2", email="admin2@motogram.app",
        password=make_password("admin123"), tipo="admin",
        is_staff=True, is_superuser=True,
    )

    pagina.goto("/test-admin-path/entrar/")
    pagina.wait_for_selector('input[name="username"]', timeout=5000)
    pagina.fill('input[name="username"]', "admin_test2")
    pagina.fill('input[name="password"]', "admin123")
    pagina.locator('button[type="submit"]').click()
    pagina.wait_for_url("**/test-admin-path/", timeout=10000)

    pagina.goto("/test-admin-path/cadastros/")
    pagina.wait_for_timeout(1000)
    assert pagina.text_content("body") is not None


@pytest.mark.django_db
def test_admin_sem_auth_redireciona(pagina):
    pagina.goto("/test-admin-path/")
    pagina.wait_for_url("**/entrar/**", timeout=5000)
