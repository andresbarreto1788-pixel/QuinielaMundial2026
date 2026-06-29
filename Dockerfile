FROM python:3.12-slim

WORKDIR /code

# Cliente de PostgreSQL (para inicializar el esquema/seed en el arranque)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Dependencias primero (mejor cacheo)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código, SQL y arranque
COPY app ./app
COPY sql ./sql
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# El entrypoint inicializa la BD (solo la 1ª vez) y luego ejecuta el comando.
ENTRYPOINT ["/entrypoint.sh"]
# Railway define $PORT; en local cae a 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
