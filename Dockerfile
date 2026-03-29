# # syntax=docker/dockerfile:1

FROM python:3.11-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --create-home --shell /bin/bash --uid 1000 --gid 1000 appuser
# Install system dependencies and Poetry

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y rclone curl gosu tzdata && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    chown -R appuser:appgroup "$POETRY_HOME" && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy the Poetry lock and pyproject files first to cache dependencies
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root --no-interaction

# Copy the rest of the application code
COPY . .

WORKDIR /code/frontend
RUN npm install && npm run build

# Copy the entrypoint script and set it as executable
COPY entrypoint.sh /entrypoint.sh

COPY migrate_db.py /code/migrate_db.py

# Set environment variables to switch between development and production
ENV APP_MODE="WEB"
ENV MAIN_LOG_LEVEL="INFO"
ENV VERSION="0.8.0-alpha.2"
ENV RCLONE_CONFIG="/config/rclone/rclone.conf"
ENV SEARCH_DEBUG=

# Use entrypoint script
ENTRYPOINT [ "/entrypoint.sh" ]
