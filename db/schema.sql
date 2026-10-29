-- Esquema de ledger-service (PostgreSQL). Generado a partir de los modelos SQLAlchemy.
-- Tambien se crea solo al arrancar el servicio (Base.metadata.create_all).

CREATE TABLE cuenta_contable (
	id_cuenta_contable UUID NOT NULL, 
	id_cuenta UUID NOT NULL, 
	saldo_actual NUMERIC(18, 2) NOT NULL, 
	moneda VARCHAR(3) NOT NULL, 
	fecha_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_cuenta_contable), 
	UNIQUE (id_cuenta)
);

CREATE TABLE transaccion (
	id_transaccion UUID NOT NULL, 
	tipo_transaccion VARCHAR(32) NOT NULL, 
	referencia VARCHAR(64) NOT NULL, 
	fecha_hora TIMESTAMP WITH TIME ZONE NOT NULL, 
	estado VARCHAR(32) NOT NULL, 
	PRIMARY KEY (id_transaccion), 
	UNIQUE (referencia)
);
CREATE INDEX idx_transaccion_referencia ON transaccion (referencia);

CREATE TABLE asiento_contable (
	id_asiento UUID NOT NULL, 
	id_transaccion UUID NOT NULL, 
	id_cuenta_contable UUID NOT NULL, 
	tipo_movimiento VARCHAR(16) NOT NULL, 
	monto NUMERIC(18, 2) NOT NULL, 
	fecha_registro TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_asiento), 
	CONSTRAINT ck_asiento_tipo_movimiento CHECK (tipo_movimiento IN ('debito','credito')), 
	CONSTRAINT ck_asiento_monto_positivo CHECK (monto > 0), 
	FOREIGN KEY(id_transaccion) REFERENCES transaccion (id_transaccion) ON DELETE CASCADE, 
	FOREIGN KEY(id_cuenta_contable) REFERENCES cuenta_contable (id_cuenta_contable) ON DELETE CASCADE
);
CREATE INDEX idx_asiento_cuenta_contable ON asiento_contable (id_cuenta_contable);
CREATE INDEX idx_asiento_transaccion ON asiento_contable (id_transaccion);
