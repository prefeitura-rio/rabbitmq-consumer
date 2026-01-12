install:
    uv sync

run:
    uv run python main.py

clean:
    find . -type d -name __pycache__ -delete
    find . -type f -name "*.pyc" -delete

docker-build:
    docker build -t rabbitmq-consumer .

docker-run:
    docker run --rm \
        -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:5672/ \
        -e QUEUE_NAME=test_queue \
        -e POLL_INTERVAL=10 \
        rabbitmq-consumer
