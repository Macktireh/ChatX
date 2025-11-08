ARG PYTHON_VERSION=3.14
ARG PYTHON_BASE=${PYTHON_VERSION}-slim-bookworm

# Base image for Python
FROM docker.io/python:${PYTHON_BASE} AS python_base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

#############################################################################################
# -------------------------------------- Build stage -------------------------------------- #
#############################################################################################
FROM python_base AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    # Dependencies for building Python packages
    build-essential \
    # Psycopg dependencies
    libpq-dev \
    # Git for VCS dependencies (optional)
    git \
    && rm -rf /var/lib/apt/lists/*

# Install PDM
RUN pip install -U pdm

ENV PDM_CHECK_UPDATE=false

# Copy dependency files
COPY pyproject.toml pdm.lock ./

# Install dependencies only (no dev dependencies for production-ready image)
RUN pdm install --prod --no-lock --no-editable

#############################################################################################
# -------------------------------------- Final stage -------------------------------------- #
#############################################################################################
FROM python_base AS final

# Create app user
RUN groupadd -r app && useradd -r -g app app

WORKDIR /project

# Copy virtual environment from builder
COPY --from=builder /build/.venv /.venv

# Set environment variables
ENV PATH="/.venv/bin:$PATH" \
    PYTHONPATH="/project" \
    DATABASE_URL=""

# Copy scripts
COPY --chown=app:app ./config config/
COPY --chown=app:app ./migrations migrations/
COPY --chown=app:app ./models models/
COPY --chown=app:app ./routes routes/
COPY --chown=app:app ./schemas schemas/
COPY --chown=app:app ./services services/
COPY --chown=app:app ./static static/
COPY --chown=app:app ./templates templates/
COPY --chown=app:app ./main.py main.py

# Switch to non-root user
USER app

EXPOSE 8000

CMD ["python", "main.py"]