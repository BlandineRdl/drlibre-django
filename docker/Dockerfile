FROM python:3.13-slim

COPY --from=astral/uv:0.11.27 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first so code edits keep this layer cached.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY config ./config
COPY scripts ./scripts
COPY static ./static
COPY docker ./docker
COPY manage.py ./

RUN useradd --create-home --uid 1000 app && chmod +x docker/entrypoint.sh
USER app

EXPOSE 8000
