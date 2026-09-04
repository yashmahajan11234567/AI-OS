# AI-OS Dockerfile
# Multi-stage build for the AI-OS Python application
# Non-root runtime user; read-only root filesystem

ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=13

# Stage 1: Build dependencies
FROM debian:${DEBIAN_VERSION}-slim AS builder

# Install build dependencies
RUN apt-get -o Acquire::Retries=3 update && \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        build-essential ca-certificates curl python3 python3-dev python3-venv libffi-dev \
        git && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /build

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Copy source code for editable install
COPY src/ ./src/

# Create virtual environment and install dependencies using uv pip
RUN uv venv /opt/ai-os/.venv && \
    uv pip install --no-cache-dir --python /opt/ai-os/.venv/bin/python -e ".[dev]"

# Stage 2: Runtime base
FROM debian:${DEBIAN_VERSION}-slim AS runtime

# Install runtime dependencies only (include python3-venv for ensurepip)
RUN apt-get -o Acquire::Retries=3 update && \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        ca-certificates curl python3 python-is-python3 python3-venv \
        libffi-dev libatomic1 \
        procps && \
    rm -rf /var/lib/apt/lists/*

# Non-root user for runtime
RUN useradd -u 10000 -m -d /opt/data -s /bin/bash ai-os

WORKDIR /opt/ai-os

# Copy virtual environment from builder
COPY --from=builder /opt/ai-os/.venv /opt/ai-os/.venv

# Install pip in the virtual environment
RUN /opt/ai-os/.venv/bin/python -m ensurepip --upgrade

# Copy application code
COPY --chmod=a+rX,go-w src/ ./src/
COPY --chmod=a+rX,go-w config/ ./config/
COPY --chmod=a+rX,go-w pyproject.toml ./
COPY --chmod=a+rX,go-w uv.lock ./
COPY --chmod=a+rX,go-w README.md ./

# Re-install the AI-OS package in editable mode to fix paths
RUN /opt/ai-os/.venv/bin/python -m pip install --no-cache-dir --no-deps -e "."

# Fix shebangs in virtual environment scripts to point to runtime python
RUN find /opt/ai-os/.venv/bin -type f -executable -exec \
    sed -i 's|^#!/build/.venv/bin/python|#!/opt/ai-os/.venv/bin/python|' {} \;

# Create required runtime directories
RUN mkdir -p /opt/data/state /opt/data/storage /opt/data/memory /opt/data/logs && \
    chown -R 10000:10000 /opt/data /opt/ai-os

# Switch to non-root user
USER 10000

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AIOS_CONFIG_PATH=/opt/ai-os/config/defaults.yaml
ENV PATH="/opt/ai-os/.venv/bin:${PATH}"

# Volume for persistent data
VOLUME [ "/opt/data" ]

# Health check - use AI-OS CLI health command
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD /opt/ai-os/.venv/bin/aios kernel health || exit 1

# Entrypoint - start AI-OS kernel
ENTRYPOINT [ "/opt/ai-os/.venv/bin/aios", "kernel", "start" ]
CMD [ "--config", "/opt/ai-os/config/defaults.yaml", "--data-dir", "/opt/data", "--log-level", "INFO" ]