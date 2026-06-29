"""Conexión a PostgreSQL y consultas SQL de la quiniela (bracket v2)."""
import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/quiniela"
)

pool = ConnectionPool(
    DATABASE_URL,
    kwargs={"row_factory": dict_row},
    min_size=1,
    max_size=10,
    open=False,
)

# ---------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------

# Tabla de posiciones: puntos derivados al vuelo con calcular_puntos().
TABLA_POSICIONES = """
SELECT
    u.nombre,
    COALESCE(SUM(calcular_puntos(p.goles_local, p.goles_visitante,
                                 m.goles_local, m.goles_visitante)), 0) AS puntos,
    COUNT(*) FILTER (
        WHERE calcular_puntos(p.goles_local, p.goles_visitante,
                              m.goles_local, m.goles_visitante) = 3
    ) AS exactos,
    COUNT(p.id) FILTER (WHERE m.estado = 'finalizado') AS jugados
FROM usuarios u
LEFT JOIN predicciones p ON p.usuario_id = u.id
LEFT JOIN partidos     m ON m.id = p.partido_id AND m.estado = 'finalizado'
GROUP BY u.id, u.nombre
ORDER BY puntos DESC, exactos DESC, u.nombre ASC;
"""

# Todos los partidos del bracket con banderas y nombres resueltos.
BRACKET = """
SELECT
    m.id, m.ronda, m.nombre_ronda, m.orden, m.estado,
    m.fecha_texto, m.sede, m.next_partido_id,
    m.goles_local, m.goles_visitante,
    m.equipo_local_id, m.equipo_visitante_id, m.ganador_equipo_id,
    el.nombre AS local,     el.bandera AS local_bandera,     el.codigo AS local_codigo,
    ev.nombre AS visitante, ev.bandera AS visitante_bandera, ev.codigo AS visitante_codigo
FROM partidos m
LEFT JOIN equipos el ON el.id = m.equipo_local_id
LEFT JOIN equipos ev ON ev.id = m.equipo_visitante_id
ORDER BY m.ronda, m.orden;
"""

ESTADISTICAS = """
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE estado = 'finalizado') AS jugados
FROM partidos;
"""

LISTAR_USUARIOS = "SELECT id, nombre FROM usuarios ORDER BY nombre;"

UPSERT_PREDICCION = """
INSERT INTO predicciones (usuario_id, partido_id, goles_local, goles_visitante)
VALUES (%(usuario_id)s, %(partido_id)s, %(goles_local)s, %(goles_visitante)s)
ON CONFLICT (usuario_id, partido_id)
DO UPDATE SET goles_local     = EXCLUDED.goles_local,
              goles_visitante = EXCLUDED.goles_visitante,
              creado_en       = now();
"""

REGISTRAR_RESULTADO = """
UPDATE partidos
SET goles_local       = %(goles_local)s,
    goles_visitante   = %(goles_visitante)s,
    ganador_equipo_id = %(ganador)s,
    estado            = 'finalizado'
WHERE id = %(partido_id)s
RETURNING id;
"""


def tabla_posiciones():
    with pool.connection() as conn:
        return conn.execute(TABLA_POSICIONES).fetchall()


def bracket():
    with pool.connection() as conn:
        return conn.execute(BRACKET).fetchall()


def estadisticas():
    with pool.connection() as conn:
        return conn.execute(ESTADISTICAS).fetchone()


def listar_usuarios():
    with pool.connection() as conn:
        return conn.execute(LISTAR_USUARIOS).fetchall()


def guardar_prediccion(usuario_id, partido_id, goles_local, goles_visitante):
    with pool.connection() as conn:
        conn.execute(UPSERT_PREDICCION, {
            "usuario_id": usuario_id, "partido_id": partido_id,
            "goles_local": goles_local, "goles_visitante": goles_visitante,
        })


def registrar_resultado(partido_id, goles_local, goles_visitante, ganador):
    with pool.connection() as conn:
        return conn.execute(REGISTRAR_RESULTADO, {
            "partido_id": partido_id, "goles_local": goles_local,
            "goles_visitante": goles_visitante, "ganador": ganador,
        }).fetchone()
