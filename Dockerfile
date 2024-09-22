FROM python:3.12.2-alpine3.19

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync

COPY main.py .
COPY carpooler ./carpooler

CMD [ "uv", "run", "main.py" ]
