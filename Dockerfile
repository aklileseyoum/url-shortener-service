# ---- Stage 1: builder ----
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --only main --no-root

# ---- Stage 2: final ----
FROM python:3.14-slim

WORKDIR /app

# Copy only the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]