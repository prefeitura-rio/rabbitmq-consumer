import logging
import os
import time
from typing import TypedDict

import pika
from pika.adapters.blocking_connection import BlockingChannel


class Config(TypedDict):
    rabbitmq_url: str
    queue_name: str
    poll_interval: int


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_env_config() -> Config:
    """Load configuration from environment variables."""
    return {
        "rabbitmq_url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "queue_name": os.getenv("QUEUE_NAME", "test_queue"),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "10")),
    }


def log_message(body: bytes) -> None:
    """Decode and log a RabbitMQ message."""
    message_body = body.decode("utf-8")
    logger.info(f"Consumed message: {message_body}")


def consume_message(channel: BlockingChannel, queue_name: str) -> None:
    """Consume a single message from queue without removing it."""
    method_frame, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)

    if method_frame:
        log_message(body)
        channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)
    else:
        logger.info("No messages available in the queue")


def consumer_loop(channel: BlockingChannel, queue_name: str, interval: int) -> None:
    """Run consumer in infinite loop with interval."""
    logger.info(f"Starting scheduled message consumption (every {interval} seconds)")

    while True:
        try:
            logger.info("Checking for messages...")
            consume_message(channel, queue_name)
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
        finally:
            time.sleep(interval)


def run_consumer_service(config: Config) -> None:
    """Run the consumer service with resource management."""
    parameters = pika.URLParameters(config["rabbitmq_url"])

    with pika.BlockingConnection(parameters) as connection:
        with connection.channel() as channel:
            channel.queue_declare(queue=config["queue_name"], durable=True)
            logger.info(f"Connected to RabbitMQ - Queue: {config['queue_name']}")
            consumer_loop(channel, config["queue_name"], config["poll_interval"])


def main() -> None:
    setup_logging()

    logger.info("Starting RabbitMQ Consumer Service")

    config = get_env_config()
    run_consumer_service(config)


if __name__ == "__main__":
    main()
