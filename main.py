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
    return {
        "rabbitmq_url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "queue_name": os.getenv("QUEUE_NAME", "test_queue"),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "10")),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8080")),
    }


@routes.get("/health")
async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "healthy"})


@routes.get("/ready")
async def ready(_: web.Request) -> web.Response:
    return web.json_response({"status": "ready"})


async def start_http_server(config: Config, routes: web.RouteTableDef) -> None:
    logger.info(f"Starting health check server on {config['host']}:{config['port']}")

    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, config["host"], config["port"])
    await site.start()


def log_message(message: AbstractIncomingMessage) -> None:
    message_body = message.body.decode("utf-8")
    logger.info(f"Consumed message: {message_body}")


async def consume_message(queue: AbstractQueue) -> None:
    try:
        message = await queue.get(no_ack=False, timeout=1.0)

        if not message:
            logger.info("No messages available in the queue")
            return

        log_message(message)

        await message.reject(requeue=True)
    except asyncio.TimeoutError:
        logger.info("No messages available in the queue")


async def check_messages(queue: AbstractQueue) -> None:
    try:
        logger.info("Checking for messages...")
        await consume_message(queue)
    except Exception as e:
        logger.error(f"Error consuming message: {e}")


async def start_queue_consumer(config: Config) -> None:
    logger.info(f"Starting RabbitMQ consumer (every {config['poll_interval']} seconds)")

    connection = await connect_robust(config["rabbitmq_url"])

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(config["queue_name"], durable=True)
        logger.info(f"Connected to RabbitMQ - Queue: {config['queue_name']}")

        while True:
            await check_messages(queue)
            await asyncio.sleep(config["poll_interval"])


async def main():
    logger.info("Starting RabbitMQ consumer service...")

    config = get_config()

    if not os.getenv("RABBITMQ_URL"):
        logger.info("Using default RabbitMQ URL")

    await asyncio.gather(
        start_http_server(config, routes),
        start_queue_consumer(config),
    )


if __name__ == "__main__":
    asyncio.run(main())
