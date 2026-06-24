"""Testes unitários para bot/services.py — chamadas HTTP ao backend."""

from unittest.mock import patch, MagicMock
import services


def _mock_resp(status_code=200, json_data=None):
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data or {}
    return m


@patch("services.requests.get")
def test_verificar_assinatura_activa(mock_get):
    mock_get.return_value = _mock_resp(200, {"active": True})
    result = services.verificar_assinatura(123)
    assert result == {"active": True}


@patch("services.requests.get")
def test_verificar_assinatura_inactiva(mock_get):
    mock_get.return_value = _mock_resp(200, {
        "active": False,
        "message": "Assinatura inativa",
    })
    result = services.verificar_assinatura(123)
    assert result["active"] is False


@patch("services.requests.get")
def test_verificar_assinatura_erro_conexao(mock_get):
    import requests as r
    mock_get.side_effect = r.RequestException("timeout")
    result = services.verificar_assinatura(123)
    assert result["message"] == "Erro de conexão com o servidor."


@patch("services.requests.post")
def test_activar_telegram_sucesso(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True})
    result = services.activar_telegram("token_valido", 999)
    assert result == {"ok": True}


@patch("services.requests.post")
def test_activar_telegram_token_invalido(mock_post):
    mock_post.return_value = _mock_resp(400, {"erro": "Token inválido"})
    result = services.activar_telegram("token_invalido", 999)
    assert "erro" in result


@patch("services.requests.post")
def test_aceitar_corrida(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True})
    result = services.aceitar_corrida(42, 999)
    assert result["ok"] is True


@patch("services.requests.post")
def test_aceitar_corrida_sem_assinatura(mock_post):
    mock_post.return_value = _mock_resp(403, {"erro": "Assinatura inativa"})
    result = services.aceitar_corrida(42, 999)
    assert result["erro"] == "Assinatura inativa"


@patch("services.requests.post")
def test_ofertar_corrida(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True, "oferta_id": 5})
    result = services.ofertar_corrida(42, 999, 15.50)
    assert result["ok"] is True


@patch("services.requests.post")
def test_recusar_corrida(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True})
    result = services.recusar_corrida(42, 999)
    assert result["ok"] is True


@patch("services.requests.post")
def test_concluir_corrida(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True})
    result = services.concluir_corrida(42, 999)
    assert result["ok"] is True


@patch("services.requests.post")
def test_concluir_corrida_erro(mock_post):
    import requests as r
    mock_post.side_effect = r.RequestException("timeout")
    result = services.concluir_corrida(42, 999)
    assert "erro" in result


@patch("services.requests.post")
def test_atualizar_localizacao(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True})
    result = services.atualizar_localizacao(999, -3.1, -60.0)
    assert result["ok"] is True


@patch("services.requests.post")
def test_atualizar_localizacao_erro_conexao(mock_post):
    import requests as r
    mock_post.side_effect = r.RequestException("timeout")
    result = services.atualizar_localizacao(999, -3.1, -60.0)
    assert "erro" in result


@patch("services.requests.post")
def test_toggle_online_activa(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True, "activo": True})
    result = services.toggle_online(999, True)
    assert result["ok"] is True
    assert result["activo"] is True


@patch("services.requests.post")
def test_toggle_online_desactiva(mock_post):
    mock_post.return_value = _mock_resp(200, {"ok": True, "activo": False})
    result = services.toggle_online(999, False)
    assert result["ok"] is True
    assert result["activo"] is False


@patch("services.requests.post")
def test_toggle_online_erro_conexao(mock_post):
    import requests as r
    mock_post.side_effect = r.RequestException("timeout")
    result = services.toggle_online(999, True)
    assert "erro" in result
