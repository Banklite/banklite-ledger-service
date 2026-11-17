"""Pruebas de INTEGRACION: endpoint + logica de negocio + base de datos.

Recorren el flujo real POST /ledger/entries -> tablas transaccion, asiento_contable
y cuenta_contable -> GET del saldo. La base es SQLite en memoria y la unica
dependencia simulada es account-service (otro microservicio).
"""
import uuid
from unittest.mock import patch

import pytest

from app.account_client import AccountUnavailable
from app.models import AsientoContable, CuentaContable, Transaccion

ORIGEN, DESTINO = uuid.uuid4(), uuid.uuid4()


def _asiento(referencia: str, monto: str = "250000.00", origen=ORIGEN, destino=DESTINO) -> dict:
    return {
        "tipo_transaccion": "transferencia",
        "referencia": referencia,
        "movimientos": [
            {"id_cuenta": str(origen), "tipo_movimiento": "debito", "monto": monto},
            {"id_cuenta": str(destino), "tipo_movimiento": "credito", "monto": monto},
        ],
    }


@pytest.fixture
def cuentas_activas():
    """account-service responde que cualquier cuenta existe y esta activa."""
    with patch("app.routers.ledger.get_account", return_value={"estado": "activa", "moneda": "COP"}) as mock:
        yield mock


def test_registrar_asiento_actualiza_los_saldos_en_la_base(client, sesiones, cuentas_activas):
    r = client.post("/ledger/entries", json=_asiento("TRF-0001"))

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "registrada" and len(cuerpo["asientos"]) == 2

    # El saldo se consulta por la API...
    assert client.get(f"/ledger/accounts/{ORIGEN}").json()["saldo_actual"] == "-250000.00"
    assert client.get(f"/ledger/accounts/{DESTINO}").json()["saldo_actual"] == "250000.00"
    # ...y queda persistido en las tres tablas.
    with sesiones() as db:
        assert db.query(Transaccion).count() == 1
        assert db.query(AsientoContable).count() == 2
        assert db.query(CuentaContable).count() == 2
    # account-service se consulto una vez por cada cuenta nueva
    assert cuentas_activas.call_count == 2


def test_la_transaccion_se_puede_consultar_despues(client, cuentas_activas):
    creada = client.post("/ledger/entries", json=_asiento("TRF-0002")).json()

    r = client.get(f"/ledger/transactions/{creada['id_transaccion']}")

    assert r.status_code == 200
    assert r.json()["referencia"] == "TRF-0002"
    assert {a["tipo_movimiento"] for a in r.json()["asientos"]} == {"debito", "credito"}


def test_dos_asientos_acumulan_saldo_y_no_repiten_la_validacion(client, cuentas_activas):
    client.post("/ledger/entries", json=_asiento("TRF-0003", "100.00"))
    client.post("/ledger/entries", json=_asiento("TRF-0004", "50.00"))

    assert client.get(f"/ledger/accounts/{DESTINO}").json()["saldo_actual"] == "150.00"
    # La cuenta contable ya existia: la segunda vez no se vuelve a llamar a account-service
    assert cuentas_activas.call_count == 2


def test_referencia_repetida_responde_409(client, cuentas_activas):
    assert client.post("/ledger/entries", json=_asiento("TRF-0005")).status_code == 201

    r = client.post("/ledger/entries", json=_asiento("TRF-0005"))

    assert r.status_code == 409
    assert "ya existe" in r.json()["detail"]


def test_asiento_descuadrado_responde_422_y_no_guarda_nada(client, sesiones, cuentas_activas):
    cuerpo = _asiento("TRF-0006")
    cuerpo["movimientos"][1]["monto"] = "1.00"

    r = client.post("/ledger/entries", json=cuerpo)

    assert r.status_code == 422
    with sesiones() as db:
        assert db.query(Transaccion).count() == 0


def test_cuenta_que_no_existe_en_account_service_responde_404(client):
    with patch("app.routers.ledger.get_account", return_value=None):
        r = client.post("/ledger/entries", json=_asiento("TRF-0007"))
    assert r.status_code == 404


def test_cuenta_suspendida_responde_409(client):
    with patch("app.routers.ledger.get_account", return_value={"estado": "suspendida"}):
        r = client.post("/ledger/entries", json=_asiento("TRF-0008"))
    assert r.status_code == 409
    assert "no esta activa" in r.json()["detail"]


def test_account_service_caido_responde_503(client):
    with patch("app.routers.ledger.get_account", side_effect=AccountUnavailable("timeout")):
        r = client.post("/ledger/entries", json=_asiento("TRF-0009"))
    assert r.status_code == 503


def test_cuenta_puente_externa_no_se_valida_contra_account_service(client, cuentas_activas):
    puente = "00000000-0000-0000-0000-000000000001"

    r = client.post("/ledger/entries", json=_asiento("ACH-0001", destino=puente))

    assert r.status_code == 201
    assert cuentas_activas.call_count == 1  # solo la cuenta del cliente
    assert client.get(f"/ledger/accounts/{puente}").json()["saldo_actual"] == "250000.00"


def test_cuenta_sin_movimientos_y_transaccion_inexistente_responden_404(client):
    assert client.get(f"/ledger/accounts/{uuid.uuid4()}").status_code == 404
    assert client.get(f"/ledger/transactions/{uuid.uuid4()}").status_code == 404


def test_stats_cuenta_las_transacciones(client, cuentas_activas):
    client.post("/ledger/entries", json=_asiento("TRF-0010"))
    assert client.get("/stats").json() == {"total_transacciones": 1}
