"""Testes dos endpoints de mapa (HERE Maps geocoding).

Cobre os 3 endpoints (/api/map/autocomplete/, /api/map/geocode/,
/api/map/reverse/) com mock das chamadas HTTP à API HERE.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.core.cache import cache
from motoristas.models import Utilizador


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.RequestException(f"HTTP {self.status_code}")


class MapAutocompleteTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.passageiro = Utilizador.objects.create_user(
            username="pass_test",
            password="test123",
            tipo="passageiro",
        )
        self.client.login(username="pass_test", password="test123")
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_sem_auth_redireciona(self):
        client = Client()
        resp = client.get("/api/map/autocomplete/?q=rua")
        self.assertEqual(resp.status_code, 302)

    def test_query_curta_retorna_vazio(self):
        resp = self.client.get("/api/map/autocomplete/?q=ab")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sugestoes"], [])

    @patch("site_publico.services.requests.get")
    def test_autocomplete_here_ok(self, mock_get):
        mock_get.return_value = _FakeResponse({
            "items": [
                {
                    "title": "Rua Quintino Bocaiúva, Maués - AM, Brasil",
                    "address": {"label": "Rua Quintino Bocaiúva, Maués - AM, Brasil"},
                    "id": "here:af:street:abc",
                }
            ]
        })
        resp = self.client.get("/api/map/autocomplete/?q=Rua Quintino Mau")
        self.assertEqual(resp.status_code, 200)
        sugestoes = resp.json()["sugestoes"]
        self.assertEqual(len(sugestoes), 1)
        self.assertEqual(sugestoes[0]["label"], "Rua Quintino Bocaiúva, Maués - AM, Brasil")
        self.assertIsNone(sugestoes[0]["lat"])
        self.assertIsNone(sugestoes[0]["lng"])

    @patch("site_publico.services.requests.get")
    def test_autocomplete_aqui_fala_nominatim_fallback(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("HERE down")
        resp = self.client.get("/api/map/autocomplete/?q=Rua Quintino")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sugestoes"], [])

    @patch("site_publico.services.requests.get")
    def test_autocomplete_cache_hit(self, mock_get):
        mock_get.return_value = _FakeResponse({
            "items": [
                {
                    "title": "Rua Teste",
                    "address": {"label": "Rua Teste"},
                    "id": "x",
                }
            ]
        })
        self.client.get("/api/map/autocomplete/?q=Rua Teste Cache")
        self.client.get("/api/map/autocomplete/?q=Rua Teste Cache")
        self.assertEqual(mock_get.call_count, 1)


class MapGeocodeTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.passageiro = Utilizador.objects.create_user(
            username="geo_test",
            password="test123",
            tipo="passageiro",
        )
        self.client.login(username="geo_test", password="test123")
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_sem_query_retorna_400(self):
        resp = self.client.get("/api/map/geocode/?q=")
        self.assertEqual(resp.status_code, 400)

    @patch("site_publico.services.requests.get")
    def test_geocode_here_ok(self, mock_get):
        mock_get.return_value = _FakeResponse({
            "items": [
                {
                    "address": {"label": "Rua Quintino Bocaiúva, 283, Maués - AM, Brasil"},
                    "position": {"lat": -3.39544, "lng": -57.7184},
                    "title": "Rua Quintino Bocaiúva, 283",
                }
            ]
        })
        resp = self.client.get("/api/map/geocode/?q=Rua Quintino Bocaiúva, 283, Maués, AM")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertAlmostEqual(data["lat"], -3.39544)
        self.assertIn("Quintino", data["label"])

    @patch("site_publico.services.requests.get")
    def test_geocode_sem_resultado_404(self, mock_get):
        mock_get.return_value = _FakeResponse({"items": []})
        resp = self.client.get("/api/map/geocode/?q=endereco inexistente xyz")
        self.assertEqual(resp.status_code, 404)


class MapReverseTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.passageiro = Utilizador.objects.create_user(
            username="rev_test",
            password="test123",
            tipo="passageiro",
        )
        self.client.login(username="rev_test", password="test123")
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_sem_coords_retorna_400(self):
        resp = self.client.get("/api/map/reverse/?")
        self.assertEqual(resp.status_code, 400)

    def test_coords_invalidas_retorna_400(self):
        resp = self.client.get("/api/map/reverse/?lat=abc&lng=xyz")
        self.assertEqual(resp.status_code, 400)

    @patch("site_publico.services.requests.get")
    def test_reverse_here_ok(self, mock_get):
        mock_get.return_value = _FakeResponse({
            "items": [
                {
                    "address": {"label": "Rua Quintino Bocaiúva, 283, Maués - AM, Brasil"},
                    "title": "Rua Quintino Bocaiúva, 283",
                }
            ]
        })
        resp = self.client.get("/api/map/reverse/?lat=-3.39544&lng=-57.7184")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Quintino", data["label"])

    @patch("site_publico.services.requests.get")
    def test_reverse_sem_resultado_404(self, mock_get):
        mock_get.return_value = _FakeResponse({"items": []})
        resp = self.client.get("/api/map/reverse/?lat=0&lng=0")
        self.assertEqual(resp.status_code, 404)
