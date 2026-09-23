# The website's live playground: the real grooming classifier behind a two-route
# HTTP wrapper (classifier/serve.py). It is a demo, not part of anyone's
# monitoring: it keeps no database, talks to no backend and logs no text.
#
#   docker build -f deploy/playground.Dockerfile -t tellmom-playground .

FROM python:3.13-slim AS deps

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /bin/uv

WORKDIR /src
COPY classifier/pyproject.toml classifier/uv.lock ./

# The lock resolves the CUDA build of torch, gigabytes of kernels a CPU VPS
# cannot use. Same pinned versions, from PyTorch's CPU index instead.
RUN uv export --locked --format requirements-txt --no-hashes --no-emit-project \
    | grep -vE '^(nvidia-|triton|cuda-)' > /tmp/requirements.txt \
    && grep -E '^torch[=<>~ ]' /tmp/requirements.txt > /tmp/torch.txt

# torch on its own layer: it is most of the image and changes only with its pin.
RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        --index-strategy unsafe-best-match \
        -r /tmp/torch.txt

RUN VIRTUAL_ENV=/opt/venv uv pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        --index-strategy unsafe-best-match \
        -r /tmp/requirements.txt \
    && rm -rf /opt/venv/lib/python3.13/site-packages/torch/test \
              /opt/venv/lib/python3.13/site-packages/torch/include \
    && find /opt/venv -name '__pycache__' -type d -prune -exec rm -rf {} +


FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # The SimCSE encoder is downloaded on first start into this volume, so a
    # redeploy reuses it instead of fetching a few hundred megabytes again.
    HF_HOME=/models \
    DEMO_HOST=0.0.0.0 \
    DEMO_PORT=8090

COPY --from=deps /opt/venv /opt/venv

# config.py reads checkpoints/ relative to the working directory.
WORKDIR /app
COPY classifier/*.py ./
COPY classifier/checkpoints/ checkpoints/

RUN useradd --system --uid 10001 --create-home tellmom \
    && mkdir -p /models && chown tellmom:tellmom /models
USER tellmom

EXPOSE 8090

# /health answers 503 until the encoder has loaded; a cold volume downloads it
# first, hence the long start period.
HEALTHCHECK --interval=15s --timeout=5s --start-period=300s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=4).status==200 else 1)"

CMD ["python", "serve.py"]
