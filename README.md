# 🏆 Quiniela Mundial 2026 · Familia Barreto (FastAPI + HTMX + PostgreSQL)

Aplicación para una quiniela familiar de la fase eliminatoria del Mundial 2026:
bracket interactivo con banderas reales, predicciones por usuario, puntuación
automática (3/1/0), cuentas de administrador, PWA instalable y diseño premium.

## 🚀 Despliegue en Railway

1. Sube este repo a GitHub (ver abajo).
2. En [railway.app](https://railway.app): **New Project → Deploy from GitHub repo** → elige este repo.
3. Añade un servicio **PostgreSQL** (New → Database → PostgreSQL).
4. En el servicio web, pestaña **Variables**, agrega:
   - `DATABASE_URL` → referencia a la del Postgres (`${{Postgres.DATABASE_URL}}`).
   - `SECRET_KEY` → una clave larga y aleatoria.
   - `ADMIN_USERS` → `usuario:clave,otro:clave` (¡cambia las claves!).
5. Railway construye con el `Dockerfile`. El contenedor **inicializa la BD la primera
   vez** (esquema + datos) y escucha en `$PORT` automáticamente.
6. En **Settings → Networking → Generate Domain** obtienes la URL pública.

> La inicialización es idempotente: solo siembra si la base está vacía, así que
> los resultados que cargues **no se borran** en los siguientes despliegues.

### 🩺 Error "connection refused 127.0.0.1:5432" en Railway
Significa que el servicio web **no tiene `DATABASE_URL`** y cae al valor local.
Arréglalo así:
1. Servicio **web** → **Variables** → **+ New Variable**.
2. Nombre `DATABASE_URL`, valor `${{Postgres.DATABASE_URL}}` (referencia al servicio Postgres).
   - El nombre `Postgres` debe coincidir con el de tu servicio de base de datos.
3. **Redeploy**. En los logs debe aparecer:
   `🗄️ Conectando a PostgreSQL en host 'postgres.railway.internal'`
   (si dice `localhost`, la variable sigue sin estar puesta).

## Arquitectura

```
.
├── sql/
│   ├── 01_schema.sql     # Tablas: usuarios, partidos, predicciones
│   ├── 02_functions.sql  # Función calcular_puntos() (3/1/0)
│   └── 03_seed.sql       # Datos iniciales (Canadá 2-1 Sudáfrica)
├── app/
│   ├── main.py           # Rutas FastAPI
│   ├── db.py             # Pool + consultas SQL
│   └── templates/        # Vistas HTML + fragmentos HTMX
├── requirements.txt
└── .env.example
```

### Lógica de puntuación (hasta el minuto 120, sin penales)
| Puntos | Condición |
|:---:|---|
| **3** | Marcador exacto |
| **1** | Falla el marcador pero acierta el signo (ganador o empate) |
| **0** | Falla marcador y signo |

Los puntos **no se guardan**: la tabla de posiciones los calcula al vuelo desde
los resultados oficiales con la función SQL `calcular_puntos()`. Una sola fuente
de verdad → cero datos desincronizados.

## Puesta en marcha

```bash
# 1) Crear la base de datos
createdb quiniela

# 2) Cargar esquema, función y datos (en orden)
psql -d quiniela -f sql/01_schema.sql
psql -d quiniela -f sql/02_functions.sql
psql -d quiniela -f sql/03_seed.sql

# 3) Dependencias de Python
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 4) Configurar conexión
copy .env.example .env          # y editar DATABASE_URL

# 5) Levantar el servidor
uvicorn app.main:app --reload
```

Abrir http://localhost:8000

## Rutas del servidor
| Método | Ruta | Descripción |
|---|---|---|
| `GET`  | `/` | Dashboard: tabla de posiciones + formulario de predicción |
| `GET`  | `/tabla` | Fragmento HTMX: tabla recalculada (auto-refresh c/30s) |
| `POST` | `/predicciones` | Guarda/actualiza una predicción (upsert) |
| `POST` | `/partidos/{id}/resultado` | (Admin) Cierra un partido y recalcula |
# QuinielaMundial2026
