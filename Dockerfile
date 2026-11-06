FROM python:3.14-slim

WORKDIR /

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY . .

CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
