import asyncio
import logging
import os
from typing import TypedDict

from aio_pika import connect_robust
from aio_pika.abc import AbstractIncomingMessage, AbstractQueue
from aiohttp import web

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Config(TypedDict):
    rabbitmq_url: str
    queue_name: str
    poll_interval: int
    host: str
    port: int


routes = web.RouteTableDef()


def get_config() -> Config:
    """Load configuration from environment variables with defaults."""
    return {
        "rabbitmq_url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "queue_name": os.getenv("QUEUE_NAME", "test_queue"),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "10")),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8080")),
    }


@routes.get("/health")
async def health(_: web.Request) -> web.Response:
    """HTTP health check endpoint for Kubernetes probes."""
    return web.json_response({"status": "healthy"})


@routes.get("/ready")
async def ready(_: web.Request) -> web.Response:
    """HTTP readiness check endpoint for Kubernetes probes."""
    return web.json_response({"status": "ready"})


async def start_http_server(config: Config, routes: web.RouteTableDef) -> None:
    """Start aiohttp server for health check endpoints."""
    logger.info(f"Starting health check server on {config['host']}:{config['port']}")

    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, config["host"], config["port"])
    await site.start()


def log_message(message: AbstractIncomingMessage) -> None:
    """Log detailed message information including body, size, and headers."""
    message_body = message.body.decode("utf-8")
    logger.info(
        f"Message consumed - Body: {message_body} | Size: {len(message_body)} bytes | Routing Key: {message.routing_key} | Headers: {message.headers}"
    )


async def consume_message(queue: AbstractQueue) -> None:
    """Consume a single message from the queue and requeue it for debugging."""
    try:
        queue_info = await queue.channel.declare_queue(queue.name, passive=True)
        message_count = queue_info.declaration_result.message_count
        logger.info(f"Queue '{queue.name}' has {message_count} messages")

        message = await queue.get(no_ack=False, timeout=1.0)

        if not message:
            logger.info("No messages available in the queue")
            return

        log_message(message)

        await message.reject(requeue=True)
        logger.info("Message requeued successfully")
    except asyncio.TimeoutError:
        logger.info("Timeout - No messages available in the queue")


async def check_messages(queue: AbstractQueue) -> None:
    """Check for messages with error handling wrapper."""
    try:
        logger.info("Checking for messages...")
        await consume_message(queue)
    except Exception as e:
        logger.error(f"Error consuming message: {e}")


async def connect_with_retry(rabbitmq_url: str):
    """Connect to RabbitMQ with exponential backoff retry logic."""
    retry_count = 0
    max_retries = 5
    base_delay = 5

    while True:
        try:
            logger.info(f"Attempting to connect to RabbitMQ at {rabbitmq_url}")
            connection = await connect_robust(rabbitmq_url)
            logger.info(f"Connected to RabbitMQ at {rabbitmq_url}")
            return connection
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                delay = base_delay * (2 ** (retry_count - 1))
                logger.error(
                    f"Failed to connect to RabbitMQ (attempt {retry_count}/{max_retries}): {e}"
                )
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Failed to connect to RabbitMQ after {max_retries} attempts. Retrying with base delay..."
                )
                retry_count = 0
                await asyncio.sleep(base_delay)


async def run_polling_loop(queue: AbstractQueue, poll_interval: int) -> None:
    """Run continuous message polling loop with configured interval."""
    loop_count = 0
    while True:
        loop_count += 1
        logger.info(f"Consumer heartbeat #{loop_count} - polling queue...")
        await check_messages(queue)
        logger.info(f"Sleeping for {poll_interval} seconds...")
        await asyncio.sleep(poll_interval)


async def start_queue_consumer(config: Config) -> None:
    """Start queue consumer with connection management and recovery."""
    logger.info(f"Starting RabbitMQ consumer (every {config['poll_interval']} seconds)")

    while True:
        try:
            connection = await connect_with_retry(config["rabbitmq_url"])

            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(config["queue_name"], durable=True)
                logger.info(f"Connected to RabbitMQ - Queue: {config['queue_name']}")

                await run_polling_loop(queue, config["poll_interval"])

        except Exception as e:
            logger.error(f"Connection lost: {e}")
            logger.info("Reconnecting...")
            await asyncio.sleep(5)


async def main():
    logger.info("Starting RabbitMQ consumer service...")

    config = get_config()

    if not os.getenv("RABBITMQ_URL"):
        logger.info("Using default RabbitMQ URL")

    tasks = [
        asyncio.create_task(start_http_server(config, routes), name="http_server"),
        asyncio.create_task(start_queue_consumer(config), name="queue_consumer"),
    ]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
