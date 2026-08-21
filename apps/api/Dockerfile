FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends curl
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Un checkout Windows (core.autocrlf) deja CRLF en el script y `sh` falla
# en la primera linea. Se normaliza dentro de la imagen para que el build
# no dependa del sistema donde se ejecuta.
RUN sed -i 's/$//' render-start.sh && chmod +x render-start.sh
EXPOSE 8000
# render-start.sh valida la configuracion, aplica migraciones pendientes
# (RUN_MIGRATIONS_ON_START) y recien despues levanta uvicorn en $PORT.
CMD ["sh", "render-start.sh"]
