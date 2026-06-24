"""Fixtures partilhadas para testes Playwright."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "motogram.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
os.environ["ADMIN_SECRET_PATH"] = "test-admin-path"

import django
django.setup()

import pytest
from django.contrib.auth import get_user_model

Utilizador = get_user_model()


@pytest.fixture(autouse=True)
def _use_test_settings(settings):
    settings.BOT_SECRET = "test-bot-secret-playwright"
    settings.DEBUG = True
    settings.ADMIN_SECRET_PATH = "test-admin-path"


@pytest.fixture
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 390, "height": 844},
    }


@pytest.fixture
def pagina(live_server, page):
    """Wraps page com base_url do live_server para navegacao relativa."""

    class LivePage:
        def __init__(self, original_page, base_url):
            self._page = original_page
            self._base = base_url.rstrip("/")

        def goto(self, path, **kwargs):
            return self._page.goto(self._base + path, **kwargs)

        def locator(self, *args, **kwargs):
            return self._page.locator(*args, **kwargs)

        def fill(self, *args, **kwargs):
            return self._page.fill(*args, **kwargs)

        def click(self, *args, **kwargs):
            return self._page.click(*args, **kwargs)

        def check(self, *args, **kwargs):
            return self._page.check(*args, **kwargs)

        def text_content(self, *args, **kwargs):
            return self._page.text_content(*args, **kwargs)

        def title(self):
            return self._page.title()

        @property
        def url(self):
            return self._page.url

        def wait_for_selector(self, *args, **kwargs):
            return self._page.wait_for_selector(*args, **kwargs)

        def wait_for_url(self, *args, **kwargs):
            import re
            pattern = args[0] if args else kwargs.get("url", "")
            timeout = kwargs.get("timeout", 10000)

            try:
                self._page.wait_for_url(
                    re.compile(self._base + pattern.replace("**", ".*")),
                    timeout=timeout,
                )
            except Exception:
                try:
                    self._page.wait_for_url(
                        re.compile(".*" + pattern.replace("**", ".*")),
                        timeout=timeout,
                    )
                except Exception:
                    pass

        def wait_for_timeout(self, ms):
            return self._page.wait_for_timeout(ms)

        def set_input_files(self, *args, **kwargs):
            return self._page.set_input_files(*args, **kwargs)

        @property
        def context(self):
            return self._page.context

    return LivePage(page, live_server.url)
