FROM python:3.13-slim

ARG USER_ID
ARG GROUP_ID

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .

RUN chown -R ${USER_ID}:${GROUP_ID} /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

USER ${USER_ID}:${GROUP_ID}

ENV PATH="/app/.venv/bin:$PATH"

VOLUME [ "/data/music" ]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]