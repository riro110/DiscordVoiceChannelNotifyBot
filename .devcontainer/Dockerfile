ARG VARIANT=3-bullseye
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y sqlite3 --no-install-recommends 

RUN pip install --upgrade pip poetry
