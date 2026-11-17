"""Prueba intencionalmente fallida para demostrar que el pipeline bloquea el despliegue.

Esta prueba NO debe fusionarse a main. Existe solo para evidenciar que, cuando una
prueba falla, el job de pruebas falla y por 'needs' no se construye la imagen ni se
despliega. Borrar esta rama despues de tomar la captura.
"""


def test_demostracion_ci_en_rojo():
    esperado = 2
    obtenido = 1 + 2  # da 3, no 2: la prueba falla a proposito
    assert obtenido == esperado, "Prueba de demostracion: CI debe quedar en rojo"
