FROM python:3.10


RUN apt-get update \ 
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    mariadb-client \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV WORKDIR /app/

WORKDIR ${WORKDIR}

COPY ./pyproject.toml ./
COPY ./poetry.lock ./

RUN pip install --upgrade pip poetry

RUN poetry install --no-dev

CMD ["poetry", "run", "python", "-m", "notifybot"]
