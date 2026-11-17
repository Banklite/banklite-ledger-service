"""Pruebas UNITARIAS: regla de partida doble (logica pura, sin base de datos ni red)."""
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import EntryCreate


def _movimiento(tipo: str, monto: str) -> dict:
    return {"id_cuenta": str(uuid.uuid4()), "tipo_movimiento": tipo, "monto": monto}


def test_asiento_balanceado_es_valido():
    # Arrange: un debito y un credito por el mismo valor
    datos = {
        "tipo_transaccion": "transferencia",
        "referencia": "REF-001",
        "movimientos": [_movimiento("debito", "150000.00"), _movimiento("credito", "150000.00")],
    }
    # Act
    asiento = EntryCreate(**datos)
    # Assert
    assert len(asiento.movimientos) == 2
    assert sum(m.monto for m in asiento.movimientos) == Decimal("300000.00")


def test_asiento_descuadrado_se_rechaza():
    datos = {
        "tipo_transaccion": "transferencia",
        "referencia": "REF-002",
        "movimientos": [_movimiento("debito", "150000"), _movimiento("credito", "149999")],
    }
    with pytest.raises(ValidationError, match="la partida doble no balancea"):
        EntryCreate(**datos)


def test_varios_movimientos_balancean_por_la_suma():
    datos = {
        "tipo_transaccion": "pago_nomina",
        "referencia": "REF-003",
        "movimientos": [
            _movimiento("debito", "300"),
            _movimiento("credito", "100"),
            _movimiento("credito", "200"),
        ],
    }
    assert len(EntryCreate(**datos).movimientos) == 3


@pytest.mark.parametrize("monto", ["0", "-5"])
def test_monto_cero_o_negativo_no_es_valido(monto):
    datos = {
        "tipo_transaccion": "transferencia",
        "referencia": "REF-004",
        "movimientos": [_movimiento("debito", monto), _movimiento("credito", monto)],
    }
    with pytest.raises(ValidationError):
        EntryCreate(**datos)


def test_un_solo_movimiento_no_es_un_asiento():
    datos = {"tipo_transaccion": "transferencia", "referencia": "REF-005", "movimientos": [_movimiento("debito", "10")]}
    with pytest.raises(ValidationError):
        EntryCreate(**datos)
