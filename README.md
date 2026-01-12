# RabbitMQ Consumer Service

A simple RabbitMQ consumer service that polls messages every 10 seconds for debugging purposes.

## Features

- Functional programming approach with SOLID, DRY, and KISS principles
- Consumes messages from a RabbitMQ queue without removing them (for debugging)
- Synchronous implementation using `pika`
- Built and managed with `uv` package manager
- Configurable via environment variables
- Docker support

## Environment Variables

- `RABBITMQ_URL`: RabbitMQ connection URL (default: `amqp://guest:guest@localhost:5672/`)
- `QUEUE_NAME`: Queue name to consume from (default: `test_queue`)
- `POLL_INTERVAL`: Interval between polls in seconds (default: `10`)

## Running Locally

1. Install uv:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Start RabbitMQ:

   ```bash
   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

4. Run the consumer:
   ```bash
   uv run python main.py
   ```

## Running with Docker

Build image:

```bash
docker build -t rabbitmq-consumer .
```

Run container:

```bash
docker run --rm \
  -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:5672/ \
  -e QUEUE_NAME=test_queue \
  -e POLL_INTERVAL=10 \
  rabbitmq-consumer
```

## Development

### Install dependencies

```bash
uv sync
```

### Run locally

```bash
uv run python main.py
```

### Clean cache

```bash
find . -type d -name __pycache__ -delete
find . -type f -name "*.pyc" -delete
```

## Testing

Access RabbitMQ management interface at http://localhost:15672 (guest/guest) to send test messages to the queue.

The consumer will read messages but **not remove them from the queue**, allowing you to debug and inspect messages repeatedly.

## Project Structure

- `main.py`: Synchronous consumer implementation
- `pyproject.toml`: Project dependencies and metadata
- `uv.lock`: Locked dependencies for reproducible builds
- `Dockerfile`: Container build configuration with uv
- `justfile`: Task runner configuration (optional)
