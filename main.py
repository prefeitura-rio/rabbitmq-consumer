import asyncio
import logging
import os
from typing import TypedDict

from aiohttp import web
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitMessage


class Config(TypedDict):
    rabbitmq_url: str
    queue_name: str
    host: str
    port: int
    logging_format: str


def get_config() -> Config:
    """Load configuration from environment variables with defaults."""
    return {
        "rabbitmq_url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "queue_name": os.getenv("QUEUE_NAME", "test_queue"),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8080")),
        "logging_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }


config = get_config()
routes = web.RouteTableDef()
logger = logging.getLogger(__name__)
broker = RabbitBroker(config["rabbitmq_url"])

logging.basicConfig(level=logging.INFO, format=config["logging_format"])


@routes.get("/health")
async def health(_: web.Request) -> web.Response:
    """HTTP health check endpoint for Kubernetes probes."""
    return web.json_response({"status": "healthy"})


@routes.get("/ready")
async def ready(_: web.Request) -> web.Response:
    """HTTP readiness check endpoint for Kubernetes probes."""
    return web.json_response({"status": "ready"})


@broker.subscriber(config["queue_name"])
async def handle_message(message: RabbitMessage) -> None:
    """Process incoming messages with logging and requeuing for debugging."""
    logger.info("Message received")

    match message.body:
        case bytes() as body:
            try:
                message_body = body.decode("utf-8")
            except UnicodeDecodeError:
                message_body = str(body)
        case _:
            message_body = str(message.body)

    logger.info(f"Message - Body: {message_body} | Size: {len(message_body)} bytes")

    await message.reject(requeue=True)
    logger.info("Message requeued successfully")


async def start_http_server(config: Config, routes: web.RouteTableDef) -> None:
    """Start aiohttp server for health check endpoints."""
    logger.info(f"Starting health check server on {config['host']}:{config['port']}")

    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, config["host"], config["port"])
    await site.start()


async def main():
    logger.info("Starting RabbitMQ consumer service...")

    if not os.getenv("RABBITMQ_URL"):
        logger.info("Using default RabbitMQ URL")

    await asyncio.gather(
        start_http_server(config, routes),
        FastStream(broker).run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
