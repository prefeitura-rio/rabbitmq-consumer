FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py ./

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

ENV RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
ENV QUEUE_NAME=test_queue
ENV POLL_INTERVAL=10

CMD ["uv", "run", "python", "main.py"]
