FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends curl
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# render-start.sh valida la configuracion, aplica migraciones pendientes
# (RUN_MIGRATIONS_ON_START) y recien despues levanta uvicorn en $PORT.
CMD ["sh", "render-start.sh"]
