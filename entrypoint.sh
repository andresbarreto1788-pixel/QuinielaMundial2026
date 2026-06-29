#!/bin/sh
# Inicializa la base de datos la PRIMERA vez (idempotente) y arranca la app.
set -e

if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Esperando a la base de datos..."
    for i in $(seq 1 30); do
        if psql "$DATABASE_URL" -c '\q' 2>/dev/null; then break; fi
        sleep 1
    done

    EXISTE=$(psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.usuarios')" 2>/dev/null || true)
    if [ -z "$EXISTE" ]; then
        echo "🌱 Inicializando esquema, funciones y datos..."
        psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/01_schema.sql
        psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/02_functions.sql
        psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/03_seed.sql
        echo "✅ Base inicializada."
    else
        echo "✔ La base ya existe; no se reinicia (se conservan los datos)."
    fi
fi

exec "$@"
