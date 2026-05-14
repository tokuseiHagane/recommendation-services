import asyncio
import logging
from litestar import Litestar, get
from litestar.status_codes import HTTP_200_OK
from litestar.response import Response
from contextlib import asynccontextmanager

from src.Ship.config.logging import configure_logging
from src.Ship.config.settings import settings
from src.Ship.tasks.kafka_worker import consume_messages
from src.Ship.Providers import container as di_container
from src.Containers.message.model.message_model import create_tables
from src.Containers.message.ports.http.message_controller import MessageController


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Litestar):
    configure_logging(settings.LOG_LEVEL)
    await create_tables()
    consumer_task = asyncio.create_task(consume_messages(di=di_container))
    logger.info("Kafka consumer started in background.")
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled.")
        logger.info("Application shutting down.")


@get("/")
async def health_check() -> Response:
    return Response(content={"status": "ok"}, status_code=HTTP_200_OK)


app = Litestar(route_handlers=[health_check, MessageController], lifespan=[lifespan])
