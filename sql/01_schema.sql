-- =====================================================================
--  Quiniela Mundial 2026 — Esquema v2 (bracket eliminatorio)
--  Ejecutar en orden: 01_schema.sql -> 02_functions.sql -> 03_seed.sql
-- =====================================================================

DROP TABLE IF EXISTS predicciones CASCADE;
DROP TABLE IF EXISTS partidos     CASCADE;
DROP TABLE IF EXISTS equipos      CASCADE;
DROP TABLE IF EXISTS usuarios      CASCADE;

-- ---------------------------------------------------------------------
-- Equipos (selecciones) con su bandera (emoji unicode)
-- ---------------------------------------------------------------------
CREATE TABLE equipos (
    id      SERIAL PRIMARY KEY,
    nombre  VARCHAR(60) NOT NULL UNIQUE,
    bandera VARCHAR(16) NOT NULL DEFAULT '🏳️',  -- emoji (fallback)
    codigo  VARCHAR(8)  NOT NULL DEFAULT 'xx'    -- ISO alpha-2 para imagen real (flagcdn)
);

-- ---------------------------------------------------------------------
-- Usuarios (participantes de la quiniela)
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(80)  NOT NULL UNIQUE,
    creado_en TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Partidos: nodos del árbol del bracket.
--   ronda:        1=16avos, 2=Octavos, 3=Cuartos, 4=Semifinal, 5=Final
--   orden:        posición dentro de la ronda (para el layout y el avance)
--   goles_*:      RESULTADO OFICIAL hasta el minuto 120 (sin penales) -> puntúa
--   ganador_*:    quién CLASIFICA (puede diferir del marcador si hubo penales)
--   next_partido: a qué partido avanza el ganador, y a qué hueco (L/V)
-- ---------------------------------------------------------------------
CREATE TABLE partidos (
    id                  SERIAL PRIMARY KEY,
    ronda               SMALLINT NOT NULL,
    nombre_ronda        VARCHAR(30) NOT NULL,
    orden               SMALLINT NOT NULL,
    equipo_local_id     INT REFERENCES equipos(id),
    equipo_visitante_id INT REFERENCES equipos(id),
    goles_local         SMALLINT CHECK (goles_local     >= 0),
    goles_visitante     SMALLINT CHECK (goles_visitante >= 0),
    ganador_equipo_id   INT REFERENCES equipos(id),
    estado              VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente', 'finalizado')),
    fecha_texto         VARCHAR(40),   -- fecha legible, p.ej. 'Lun 29 jun · 17:30'
    sede                VARCHAR(80),   -- estadio y ciudad
    next_partido_id     INT REFERENCES partidos(id),
    next_slot           CHAR(1) CHECK (next_slot IN ('L', 'V')),
    UNIQUE (ronda, orden)
);

-- ---------------------------------------------------------------------
-- Predicciones: una por usuario y por partido
-- ---------------------------------------------------------------------
CREATE TABLE predicciones (
    id              SERIAL PRIMARY KEY,
    usuario_id      INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    partido_id      INT NOT NULL REFERENCES partidos(id) ON DELETE CASCADE,
    goles_local     SMALLINT NOT NULL CHECK (goles_local     >= 0),
    goles_visitante SMALLINT NOT NULL CHECK (goles_visitante >= 0),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, partido_id)
);

CREATE INDEX idx_pred_partido ON predicciones (partido_id);
CREATE INDEX idx_pred_usuario ON predicciones (usuario_id);
CREATE INDEX idx_partidos_ronda ON partidos (ronda, orden);
