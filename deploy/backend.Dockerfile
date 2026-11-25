# One image for every Python service (01-interfaces.md §2). Every FROM is
# pinned by digest (C16); check_pins.py fails CI otherwise.
#
# Targets:
#   runtime  - all backend services (web-less): agents, mcp-server, ingestion,
#              parser, fetcher, release
#   web      - runtime + the built React app (served by the web service)

FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

# ---------------------------------------------------------------- deps
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS deps
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src/backend
COPY backend/pyproject.toml backend/uv.lock ./
# --frozen: install exactly the hash-locked set; fail if uv.lock is stale.
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------- frontend
FROM node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a AS frontend
WORKDIR /src/frontend
COPY frontend/ ./
# Install scripts are off (C14). Until A adds package.json the stage yields an
# empty dist/ so the stack still builds.
RUN if [ -f package-lock.json ]; then \
        npm ci --ignore-scripts --no-audit --no-fund && npm run build; \
    else \
        mkdir -p dist; \
    fi

# ---------------------------------------------------------------- runtime
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS runtime
RUN groupadd --system --gid 10001 rubrica \
 && useradd --system --uid 10001 --gid rubrica --no-create-home --shell /usr/sbin/nologin rubrica \
 && mkdir -p /data/parse-in /data/parse-out /data/uploads \
 && chown -R 10001:10001 /data
COPY --from=deps /opt/venv /opt/venv
COPY backend /app/backend
COPY seed /app/seed
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
USER 10001:10001
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD ["python", "-m", "backend.common.healthcheck"]

# ---------------------------------------------------------------- web
FROM runtime AS web
COPY --from=frontend --chown=10001:10001 /src/frontend/dist /app/frontend_dist

# ---------------------------------------------------------------- embeddings
FROM deps AS embedding-assets
RUN uv sync --frozen --no-dev --no-install-project --extra embedding
COPY scripts/stage_embedding.py /tmp/stage_embedding.py
COPY aibom/models.lock /opt/models/models.lock
RUN python /tmp/stage_embedding.py /opt/models/models.lock /opt/models/bge-small-en-v1.5

FROM runtime AS embedding
COPY --from=embedding-assets /opt/venv /opt/venv
COPY --from=embedding-assets /opt/models /opt/models
