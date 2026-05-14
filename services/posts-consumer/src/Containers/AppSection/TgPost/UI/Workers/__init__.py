"""TgPost Workers: Kafka workers для обработки сообщений."""

from .ConsumerWorker import ConsumerWorker
from .ChannelsDiffWorker import ChannelsDiffWorker

__all__ = [
    "ConsumerWorker",
    "ChannelsDiffWorker",
]
