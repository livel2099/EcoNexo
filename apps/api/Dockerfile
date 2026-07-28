FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 1001 econexo \
    && useradd --system --uid 1001 --gid econexo --home-dir /app econexo

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=econexo:econexo . .
RUN python -m compileall -q app \
    && chmod +x /app/render-start.sh

USER econexo
EXPOSE 10000
STOPSIGNAL SIGTERM

CMD ["/app/render-start.sh"]
