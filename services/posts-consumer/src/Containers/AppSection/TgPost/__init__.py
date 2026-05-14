"""
TgPost Container: Обработка постов из Telegram каналов.

Porto Architecture Container для динамических Kafka консьюмеров.
"""

from .Providers import TgPostProvider

__all__ = ["TgPostProvider"]
