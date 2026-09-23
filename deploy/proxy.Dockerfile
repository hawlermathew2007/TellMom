# The Leesin proxy: the only TellMom process that runs in public. It relays
# sealed traffic between parents' browsers and their own servers, and keeps
# nothing but server accounts in its database. Build context is the repository
# root: the proxy imports shared/.
#
#   docker build -f deploy/proxy.Dockerfile -t tellmom-proxy .

FROM python:3.13-slim AS deps

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /bin/uv

WORKDIR /src
COPY pyproject.toml uv.lock ./

# The lock is shared with the backend and adapters, so it carries more than the
# proxy imports; installing it whole keeps one pinned set across every process.
RUN uv venv /opt/venv \
    && uv export --locked --format requirements-txt --no-hashes --no-emit-project > /tmp/requirements.txt \
    && VIRTUAL_ENV=/opt/venv uv pip install -r /tmp/requirements.txt \
    && find /opt/venv -name '__pycache__' -type d -prune -exec rm -rf {} +


FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8080

COPY --from=deps /opt/venv /opt/venv

WORKDIR /app
COPY proxy/ proxy/
COPY shared/ shared/

RUN useradd --system --uid 10001 tellmom
USER tellmom

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4).status==200 else 1)"

# Behind Traefik: trust its X-Forwarded-* so redirects and WebSocket
# URLs come out https.
CMD ["uvicorn", "proxy.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
