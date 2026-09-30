FROM python:3.12-slim AS wheels

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.lock.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.lock.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DCX_RUNTIME_VERSION=1.1.6 \
    DCX_RUNTIME_ROOT=/app/runtime \
    DCX_ASSET_BASE_URL=http://runtime-assets/v1.1.6 \
    DCX_LOCAL_ASSET_ROOT=/app/runtime-assets \
    PORT=8080

RUN useradd --create-home --uid 10001 dcx \
    && mkdir -p /app/runtime /app/src \
    && chown -R dcx:dcx /app

COPY --from=wheels /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

WORKDIR /app/src
COPY --chown=dcx:dcx app ./app
COPY --chown=dcx:dcx r2_upload/v1.1.6 /app/runtime-assets
RUN chmod 0444 "app/canonical/Master DharmaCodex V 1.1.6 Internal Reading Renderers Code.PY"

USER dcx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4).read()"

CMD ["uvicorn", "app.service:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--log-level", "warning"]

