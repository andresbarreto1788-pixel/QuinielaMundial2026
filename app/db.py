"""Conexión a PostgreSQL y consultas SQL de la quiniela (bracket v2)."""
import os
import sys
from urllib.parse import urlsplit

DEFAULT_LOCAL = "postgresql://postgres:postgres@localhost:5432/quiniela"

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_LOCAL)

# Railway/Heroku a veces entregan el esquema 'postgres://'; psycopg usa 'postgresql://'.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Log de diagnóstico (sin exponer la contraseña): a qué host:puerto nos conectamos.
_host = urlsplit(DATABASE_URL).hostname or "?"
if not os.environ.get("DATABASE_URL"):
    print("⚠️  DATABASE_URL no está definida: usando localhost (solo sirve en tu PC, "
          "NO en Railway). Define DATABASE_URL en el servicio web.", file=sys.stderr)
print(f"🗄️  Conectando a PostgreSQL en host '{_host}'", file=sys.stderr)

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

# Info básica de un partido (para la cabecera de la lista de predicciones)
INFO_PARTIDO = """
SELECT m.id, m.estado, m.goles_local, m.goles_visitante,
       el.nombre AS local,     el.codigo AS local_codigo,
       ev.nombre AS visitante, ev.codigo AS visitante_codigo
FROM partidos m
LEFT JOIN equipos el ON el.id = m.equipo_local_id
LEFT JOIN equipos ev ON ev.id = m.equipo_visitante_id
WHERE m.id = %s;
"""

# Predicciones de todos los usuarios para un partido (con puntos si ya se jugó)
PREDS_PARTIDO = """
SELECT u.nombre, p.goles_local, p.goles_visitante,
       calcular_puntos(p.goles_local, p.goles_visitante,
                       m.goles_local, m.goles_visitante) AS puntos
FROM predicciones p
JOIN usuarios u ON u.id = p.usuario_id
JOIN partidos m ON m.id = p.partido_id
WHERE p.partido_id = %s
ORDER BY puntos DESC, u.nombre ASC;
"""

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

# Deshacer un resultado cargado por error: el partido vuelve a 'pendiente',
# se borra el marcador y el clasificado. Devuelve a qué partido avanzaba el
# ganador (next_*) para limpiar también ese hueco del bracket.
RESETEAR_RESULTADO = """
UPDATE partidos
SET goles_local       = NULL,
    goles_visitante   = NULL,
    ganador_equipo_id = NULL,
    estado            = 'pendiente'
WHERE id = %(partido_id)s
RETURNING id, next_partido_id, next_slot;
"""

LIMPIAR_HUECO_LOCAL     = "UPDATE partidos SET equipo_local_id     = NULL WHERE id = %s;"
LIMPIAR_HUECO_VISITANTE = "UPDATE partidos SET equipo_visitante_id = NULL WHERE id = %s;"

# ¿El siguiente partido ya tiene resultado cargado? Si es así, no debemos
# vaciar su hueco a ciegas (rompería una ronda posterior ya jugada).
ESTADO_PARTIDO = "SELECT estado FROM partidos WHERE id = %s;"


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


def info_partido(partido_id):
    with pool.connection() as conn:
        return conn.execute(INFO_PARTIDO, (partido_id,)).fetchone()


def predicciones_de_partido(partido_id):
    with pool.connection() as conn:
        return conn.execute(PREDS_PARTIDO, (partido_id,)).fetchall()


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


def resetear_resultado(partido_id):
    """Deshace el resultado de un partido (cargado por error).

    - Vuelve el partido a 'pendiente' y borra marcador/clasificado.
    - Saca al equipo que ya había avanzado al siguiente partido del bracket,
      siempre que ese siguiente partido NO esté ya finalizado (en cuyo caso
      se deja intacto para no romper una ronda posterior ya jugada).

    Las predicciones se conservan: simplemente dejan de puntuar hasta que se
    vuelva a cargar el resultado correcto.

    Devuelve None si el partido no existe.
    """
    with pool.connection() as conn:
        fila = conn.execute(RESETEAR_RESULTADO, {"partido_id": partido_id}).fetchone()
        if fila is None:
            return None

        next_id, slot = fila["next_partido_id"], fila["next_slot"]
        if next_id and slot:
            siguiente = conn.execute(ESTADO_PARTIDO, (next_id,)).fetchone()
            if siguiente and siguiente["estado"] != "finalizado":
                sql = LIMPIAR_HUECO_LOCAL if slot == "L" else LIMPIAR_HUECO_VISITANTE
                conn.execute(sql, (next_id,))
        return fila
