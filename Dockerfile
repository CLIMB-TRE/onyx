# syntax=docker/dockerfile:1

# TODO: Use docker label for onyx version
# TODO: Pin versions for poetry and the export plugin

ARG PYTHON_VERSION=3.11.8
# ARG POETRY_VERSION=
# ARG_POETRY_EXPORT_VERSION=

###################################################
#       STAGE 1: Poetry requirements export
###################################################
FROM python:${PYTHON_VERSION}-slim AS poetry-export

# Install Poetry and export plugin
RUN pip install --no-cache-dir poetry poetry-plugin-export

# Set up working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

RUN \
    # Export poetry lockfile requirements to requirements.txt
    poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    # Export onyx version from pyproject.toml
    poetry version > version

###################################################
#          STAGE 2: Application runtime
###################################################
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV \
    # Prevents Python from writing pyc files.
    PYTHONDONTWRITEBYTECODE=1 \
    # Keeps Python from buffering stdout and stderr to avoid situations where
    # the application crashes without emitting any logs due to buffering.
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,from=poetry-export,source=/app/requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Copy onyx version from poetry export stage
COPY --from=poetry-export /app/version .

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY onyx .

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD ["gunicorn", "-c", "onyx.gunicorn.py", "--bind", "0.0.0.0:8000"]
