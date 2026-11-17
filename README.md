# Ledger Service — BankLite

[![CI](https://github.com/Banklite/banklite-ledger-service/actions/workflows/ci.yml/badge.svg)](https://github.com/Banklite/banklite-ledger-service/actions/workflows/ci.yml)
[![Deploy](https://github.com/Banklite/banklite-ledger-service/actions/workflows/deploy.yml/badge.svg)](https://github.com/Banklite/banklite-ledger-service/actions/workflows/deploy.yml)

Libro contable de doble partida, append-only. Es la fuente de verdad del saldo de cada cuenta.

Parte del proyecto **BankLite** (banca digital con microservicios) de *Arquitectura y Modelamiento de Software*, Universidad Cooperativa de Colombia. Cada microservicio tiene su propio repositorio y su propia base de datos (`ledger_db`).

## Responsabilidad en la arquitectura

Libro contable de doble partida, append-only. Es la fuente de verdad del saldo de cada cuenta. Se comunica con los demas servicios por **REST** (operaciones que necesitan respuesta inmediata) y por **eventos** en RabbitMQ (exchange `banklite.events`, tipo topic).

| Eventos publicados | Eventos consumidos |
|---|---|
| — | — |

## Tecnologias

FastAPI, SQLAlchemy, PostgreSQL. Python 3.12, Docker.

## Despliegue

- URL publica: <https://banklite-ledger-service.onrender.com>
- Salud: <https://banklite-ledger-service.onrender.com/health>
- Documentacion interactiva (Swagger): <https://banklite-ledger-service.onrender.com/docs>

Desplegado en Render (plan gratuito: tarda hasta ~1 minuto en responder si estuvo inactivo). Las credenciales se configuran como variables de entorno en la plataforma, no en el codigo.

## Endpoints principales

| Metodo | Ruta | Descripcion |
|---|---|---|
| `POST` | `/ledger/entries` | Registra una transaccion con sus asientos (debito/credito) |
| `GET` | `/ledger/accounts/{id_cuenta}` | Saldo de la cuenta |
| `GET` | `/ledger/transactions/{id_transaccion}` | Detalle de una transaccion y sus asientos |
| `GET` | `/health` | Estado del servicio |
| `GET` | `/stats` | Contadores del servicio |

La lista completa esta en `/docs`.

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores.

| Variable | Descripcion |
|---|---|
| `DATABASE_URL` | Conexion PostgreSQL |
| `ACCOUNT_SERVICE_URL` | URL de account-service (valida que la cuenta exista) |

## Base de datos

Motor: PostgreSQL. Base: `ledger_db`.

- `db/schema.sql`: creacion de tablas, indices y restricciones.
- `db/seed.sql`: datos de ejemplo.

El servicio tambien crea las tablas solo al arrancar (`create_all`). Para restaurar a mano:

```bash
createdb ledger_db
psql -d ledger_db -f db/schema.sql
psql -d ledger_db -f db/seed.sql
```

Respaldo completo (para entregar o restaurar): `pg_dump -Fc ledger_db > ledger_db.dump` y `pg_restore -d ledger_db ledger_db.dump`.

## Instalacion y ejecucion

Con Docker:

```bash
docker build -t banklite-ledger-service .
docker run --env-file .env -p 8003:8003 -e PORT=8003 banklite-ledger-service
```

Sin Docker:

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

Prueba: abre <http://localhost:8003/docs>.

## Pruebas automatizadas

```bash
pip install -r requirements-dev.txt
python -m pytest tests -v --cov=app --cov-report=term-missing --cov-report=html
```

No necesitan PostgreSQL, RabbitMQ ni los otros microservicios: la base es SQLite en memoria y las dependencias externas se reemplazan con mocks (`unittest.mock`). El reporte navegable queda en `htmlcov/index.html`.

| Tipo | Archivo | Que verifica |
|---|---|---|
| Unitaria | `tests/unit/test_partida_doble.py` | Regla de partida doble: un asiento solo es valido si debitos = creditos; montos positivos y minimo dos movimientos. |
| Unitaria (mocks) | `tests/unit/test_account_client.py` | Cliente REST hacia account-service con `httpx` simulado: cuenta existente, 404, 5xx y fallo de red. |
| Integracion | `tests/integration/test_ledger_api.py` | `POST /ledger/entries` -> tablas `transaccion`, `asiento_contable` y `cuenta_contable` -> saldo por `GET`; referencia duplicada, cuenta inactiva y account-service caido. |
| Integracion | `tests/integration/test_metrics.py` | `GET /metrics` cuenta las peticiones por ruta y codigo de estado, publica la latencia y no se cuenta a si mismo. |

Resultado actual: **25 pruebas** (10 unitarias y 15 de integracion), todas aprobadas, con **96 % de cobertura** de `app/`. El pipeline exige un minimo de 70 %.

## Monitoreo con Prometheus y Grafana

El servicio expone sus metricas en `GET /metrics` (libreria `prometheus-client`, modulo `app/metrics.py`):

| Senal | Metrica | Tipo |
|---|---|---|
| Trafico | `http_requests_total{method, path, status}` | Counter |
| Errores | `http_requests_total{status=~"5.."}` | Counter |
| Latencia | `http_request_duration_seconds` | Histogram |
| Saturacion | `http_requests_in_progress`, `process_resident_memory_bytes` | Gauge |

La etiqueta `path` es la ruta declarada (por ejemplo `/accounts/{id_cuenta}`), no la URL: asi un id distinto no crea una serie nueva.

La configuracion esta versionada en `monitoring/`:

| Archivo | Para que sirve |
|---|---|
| `prometheus.yml` | A quien consulta Prometheus y cada cuanto (15 s) |
| `alertas.yml` | Alertas: servicio caido, mas de 5 % de errores 5xx, latencia p95 mayor a 1 s |
| `docker-compose.yml` | Levanta Prometheus y Grafana |
| `grafana/dashboards/banklite.json` | Dashboard con disponibilidad, peticiones, tiempos de respuesta y tasa de errores |
| `grafana/provisioning/` | Conecta Grafana con Prometheus y carga el dashboard al arrancar |

```bash
cd monitoring
docker compose up -d
```

- Prometheus: <http://localhost:9090> — en *Status > Targets* el servicio debe aparecer en **UP**.
- Grafana: <http://localhost:3000> (usuario `admin`, clave `admin`) — carpeta *BankLite*, dashboard *Cuatro senales doradas*.

`monitoring/prometheus.yml` consulta a este servicio en Render. El tablero del sistema completo, con todos los microservicios, esta en `banklite-api-gateway/monitoring`.

Render (plan gratuito) duerme el servicio tras 15 minutos sin trafico. La primera consulta lo despierta y puede tardar cerca de un minuto, por eso el target puede verse en DOWN al comienzo. Mientras Prometheus este encendido el servicio no se duerme y consume horas del plan: apaga el stack con `docker compose down` cuando termines.

## CI/CD y estrategia de ramas

Los workflows estan en `.github/workflows/`:

| Archivo | Cuando corre | Que hace |
|---|---|---|
| `ci.yml` | Cada `push` a una rama y cada `pull request` hacia `main` | Instala dependencias, compila, ejecuta las pruebas unitarias y de integracion, mide la cobertura (minimo 70 %), sube el reporte como artefacto `coverage-banklite-ledger-service` y comprueba que la imagen Docker construye |
| `deploy.yml` | Cada cambio integrado en `main` (o a mano) | Ejecuta `ci.yml`; si pasa, publica la imagen en GitHub Container Registry y pide el despliegue a Render |

Los jobs de `deploy.yml` estan encadenados con `needs`: si una sola prueba falla, no se construye la imagen ni se despliega. El Deploy Hook de Render es una credencial y esta en *Settings > Secrets and variables > Actions* como `RENDER_DEPLOY_HOOK_URL`; si falta, el despliegue falla en vez de terminar en verde sin desplegar.

Estrategia de ramas:

1. `main` es la rama desplegada. No se trabaja directamente sobre ella.
2. Cada cambio se hace en una rama corta (`feat/...`, `fix/...`, `test/...`). Cada `push` ejecuta `ci.yml`.
3. Se abre un pull request hacia `main`. El check de CI debe estar en verde para fusionar.
4. Al fusionar, `deploy.yml` vuelve a ejecutar las pruebas y despliega.

## Repositorios del proyecto

`banklite-identity-service`, `banklite-account-service`, `banklite-ledger-service`, `banklite-transfer-service`, `banklite-card-service`, `banklite-fraud-service`, `banklite-notification-service`, `banklite-compliance-service`. Gateway: `banklite-api-gateway`. Panel web: `banklite-web-panel`.
