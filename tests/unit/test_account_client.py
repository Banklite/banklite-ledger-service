"""Pruebas UNITARIAS del cliente REST hacia account-service.

account-service se reemplaza con un mock de httpx.get: se comprueba como
reacciona ledger a cada respuesta posible sin hacer ninguna llamada de red.
"""
import uuid
from unittest.mock import Mock, patch

import httpx
import pytest

from app.account_client import AccountUnavailable, get_account

ID_CUENTA = uuid.uuid4()


def _respuesta(status_code: int, cuerpo: dict | None = None) -> httpx.Response:
    return httpx.Response(status_code, json=cuerpo or {}, request=httpx.Request("GET", "http://account-service"))


@patch("app.account_client.httpx.get")
def test_cuenta_existente_devuelve_sus_datos(mock_get: Mock):
    mock_get.return_value = _respuesta(200, {"id_cuenta": str(ID_CUENTA), "estado": "activa", "moneda": "COP"})

    cuenta = get_account(ID_CUENTA)

    assert cuenta["estado"] == "activa"
    mock_get.assert_called_once()
    assert mock_get.call_args.args[0].endswith(f"/accounts/{ID_CUENTA}")


@patch("app.account_client.httpx.get")
def test_cuenta_inexistente_devuelve_none(mock_get: Mock):
    mock_get.return_value = _respuesta(404)
    assert get_account(ID_CUENTA) is None


@patch("app.account_client.httpx.get")
def test_error_5xx_se_traduce_a_account_unavailable(mock_get: Mock):
    mock_get.return_value = _respuesta(503)
    with pytest.raises(AccountUnavailable, match="503"):
        get_account(ID_CUENTA)


@patch("app.account_client.httpx.get")
def test_fallo_de_red_se_traduce_a_account_unavailable(mock_get: Mock):
    mock_get.side_effect = httpx.ConnectError("conexion rechazada")
    with pytest.raises(AccountUnavailable):
        get_account(ID_CUENTA)
