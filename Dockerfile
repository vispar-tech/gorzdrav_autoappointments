FROM python:3.12-slim-bullseye

RUN pip install poetry==2.0.1

# Configuring poetry
RUN poetry config virtualenvs.create false
RUN poetry config cache-dir /tmp/poetry_cache

# Copying requirements of a project
WORKDIR /usr/src

COPY pyproject.toml poetry.lock ./

# Installing requirements
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

# Copying actuall application
COPY ./bot ./bot
COPY alembic.ini ./alembic.ini


CMD ["python", "-m", "bot"]

