# RabbitMQ Consumer Service

An asynchronous RabbitMQ consumer service with health check endpoints that polls messages every 10 seconds for debugging purposes.

## Features

- Functional programming approach with SOLID, DRY, and KISS principles
- Consumes messages from a RabbitMQ queue without removing them (for debugging)
- Asynchronous implementation using `aio-pika`
- Built-in HTTP health check server with `/health` and `/ready` endpoints
- Built and managed with `uv` package manager
- Configurable via environment variables
- Docker support
- Kubernetes deployment ready

## Environment Variables

- `RABBITMQ_URL`: RabbitMQ connection URL (default: `amqp://guest:guest@localhost:5672/`)
- `QUEUE_NAME`: Queue name to consume from (default: `test_queue`)
- `POLL_INTERVAL`: Interval between polls in seconds (default: `10`)
- `HOST`: HTTP server host (default: `0.0.0.0`)
- `PORT`: HTTP server port (default: `8080`)

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
  -p 8080:8080 \
  -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:5672/ \
  -e QUEUE_NAME=test_queue \
  -e POLL_INTERVAL=10 \
  rabbitmq-consumer
```

The service will be available at:
- Health check: http://localhost:8080/health
- Readiness check: http://localhost:8080/ready

## Development

### Install dependencies

```bash
uv sync
```

### Run locally

```bash
uv run python main.py
```

### Using Just (task runner)

```bash
# Install dependencies
just install

# Run the service
just run

# Build Docker image
just docker-build

# Run Docker container
just docker-run

# Clean Python cache files
just clean
```

## Testing

Access RabbitMQ management interface at http://localhost:15672 (guest/guest) to send test messages to the queue.

The consumer will read messages but **not remove them from the queue**, allowing you to debug and inspect messages repeatedly.

### Health Checks

The service provides HTTP endpoints for monitoring:

- `GET /health` - Returns `{"status": "healthy"}`
- `GET /ready` - Returns `{"status": "ready"}`

## Kubernetes Deployment

The project includes Kubernetes manifests in the `k8s/` directory for easy deployment.

## Project Structure

- `main.py`: Asynchronous consumer implementation with HTTP health checks
- `pyproject.toml`: Project dependencies and metadata
- `uv.lock`: Locked dependencies for reproducible builds
- `Dockerfile`: Container build configuration with uv
- `justfile`: Task runner configuration
- `k8s/`: Kubernetes deployment manifests
- `.github/workflows/`: CI/CD pipeline configuration
