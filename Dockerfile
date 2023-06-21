FROM python:3.11-slim

ARG USER=unprivileged
ARG GROUP=unprivileged
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update && \
    apt-get -qq install --no-install-recommends apt-transport-https ca-certificates locales git curl && \
    update-ca-certificates --fresh && \
    apt-get -qq upgrade --no-install-recommends
RUN pip install --upgrade pip poetry
RUN addgroup $GROUP && adduser \
    --disabled-password \
    --gecos "" \
    --ingroup $GROUP \
    --uid 1000 \
    $USER

COPY . /app
WORKDIR /app
RUN rm -rf /app/dist && poetry build && python -m venv /app/.venv
RUN . /app/.venv/bin/activate && pip install /app/dist/s3proxy-*.whl

EXPOSE 5000
USER $USER

# TODO: use gunicorn https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker#gunicorn_conf
CMD . /app/.venv/bin/activate && uvicorn --host 0.0.0.0 --port 5000 --factory s3proxy:main.app_factory
