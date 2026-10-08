# ==========================================================================
# Teepresso — production image (multi-stage, non-root, healthcheck)
# Build:  docker build -t teepresso .
# Run:    docker compose up --build      (preferred — see docker-compose.yml)
# ==========================================================================

# --- Stage 1: build wheels (keeps the final image free of compilers) ------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# --- Stage 2: runtime -----------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8000

# runtime-only system libs (no compilers in the final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 libjpeg62-turbo zlib1g curl \
    && rm -rf /var/lib/apt/lists/*

# install pre-built wheels
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# non-root user
RUN useradd --create-home --uid 1000 teepresso
WORKDIR /app

COPY --chown=teepresso:teepresso . .
RUN chmod +x deploy/entrypoint.sh \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R teepresso:teepresso /app

USER teepresso
EXPOSE 8000

# container health: hit Django; any HTTP response (200/302) means the app is up
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/accounts/login/" || exit 1

ENTRYPOINT ["deploy/entrypoint.sh"]
CMD ["gunicorn", "--chdir", "/app/teepresso_site", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--threads", "2", \
     "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
