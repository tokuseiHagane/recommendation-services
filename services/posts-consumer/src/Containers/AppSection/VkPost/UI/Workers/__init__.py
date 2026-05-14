"""VkPost Workers: Kafka workers для VK данных."""

from src.Containers.AppSection.VkPost.UI.Workers.VkConsumerWorker import VkConsumerWorker
from src.Containers.AppSection.VkPost.UI.Workers.VkGroupsDiffWorker import VkGroupsDiffWorker

__all__ = ["VkConsumerWorker", "VkGroupsDiffWorker"]
