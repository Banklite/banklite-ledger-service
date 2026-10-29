# Ledger Service — BankLite

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

## Repositorios del proyecto

`banklite-identity-service`, `banklite-account-service`, `banklite-ledger-service`, `banklite-transfer-service`, `banklite-card-service`, `banklite-fraud-service`, `banklite-notification-service`, `banklite-compliance-service`. Panel web: `services/web-panel` en el repositorio `banklite-microservicios`.
