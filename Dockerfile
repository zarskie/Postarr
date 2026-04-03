# # syntax=docker/dockerfile:1

FROM python:3.11-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --create-home --shell /bin/bash --uid 1000 --gid 1000 appuser

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv


RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y rclone curl gosu tzdata && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy the lock and pyproject files first to cache dependencies
COPY pyproject.toml uv.lock ./
ENV VIRTUAL_ENV=/code/.venv
ENV PATH="/code/.venv/bin:$PATH"

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Copy the rest of the application code
COPY . .

WORKDIR /code/frontend
RUN npm install && npm run build

# Copy the entrypoint script and set it as executable
COPY entrypoint.sh /entrypoint.sh

COPY migrate_db.py /code/migrate_db.py

# Set environment variables to switch between development and production
ARG GIT_SHA
ARG GIT_RUN_NUMBER
ENV GIT_SHA=$GIT_SHA
ENV GIT_RUN_NUMBER=$GIT_RUN_NUMBER
ENV MAIN_LOG_LEVEL="INFO"
ENV VERSION="0.9.0-alpha.3"
ENV RCLONE_CONFIG="/config/rclone/rclone.conf"
ENV SEARCH_DEBUG=
ENV TIME_FORMAT="12"

# Use entrypoint script
ENTRYPOINT [ "/entrypoint.sh" ]
