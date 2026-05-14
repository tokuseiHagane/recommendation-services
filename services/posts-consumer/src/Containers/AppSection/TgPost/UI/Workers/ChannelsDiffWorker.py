"""
ChannelsDiffWorker: Прослушивание tg_channels_diff для создания консьюмеров.

Porto Architecture Worker:
- Прослушивает топик tg_channels_diff
- Создает новые консьюмеры через CreateDynamicConsumerAction
- Запускает ConsumerWorker для новых каналов
"""

import asyncio
import json
from typing import Any
import logging

from aiokafka import AIOKafkaConsumer

from src.Containers.AppSection.TgPost.Actions.CreateDynamicConsumerAction import create_dynamic_consumer_action
from src.Containers.AppSection.TgPost.UI.Workers.ConsumerWorker import ConsumerWorker

logger = logging.getLogger(__name__)


class ChannelsDiffWorker:
    """
    Worker: Прослушивание tg_channels_diff для реактивного создания консьюмеров.
    
    Workflow:
    1. Consume события о новых каналах из tg_channels_diff
    2. Создать новый консьюмер (CreateDynamicConsumerAction)
    3. Запустить ConsumerWorker для нового канала
    
    Graceful shutdown:
    - Устанавливает флаг _running = False
    - Останавливает consumer
    - Возвращает управление
    
    Usage:
        worker = ChannelsDiffWorker(
            bootstrap_servers="localhost:9092",
            cache=cache,
            manager=manager
        )
        await worker.start()  # Блокирующий вызов
        
        # В другой корутине для остановки:
        await worker.stop()
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        cache: Any,  # PostObjectsCache
        manager: Any,  # DynamicConsumerManager
        group_id: str = "channels-diff-consumer"
    ):
        """
        Initialize ChannelsDiffWorker.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            cache: PostObjectsCache instance
            manager: DynamicConsumerManager instance
            group_id: Consumer group ID
        """
        self._bootstrap_servers = bootstrap_servers
        self._cache = cache
        self._manager = manager
        self._group_id = group_id
        self._running = False
        self._consumer: Any = None  # AIOKafkaConsumer
        logger.info("ChannelsDiffWorker initialized")
    
    async def start(self):
        """
        Запустить worker loop.
        
        Блокирующий вызов, работает до вызова stop().
        Создает consumer для tg_channels_diff и обрабатывает события.
        """
        self._running = True
        
        # Создать consumer для tg_channels_diff
        self._consumer = AIOKafkaConsumer(
            "tg_channels_diff",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True  # Auto commit для упрощения
        )
        
        await self._consumer.start()
        
        logger.info(
            "ChannelsDiffWorker started, listening to tg_channels_diff"
        )
        
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                
                try:
                    # Parse channel data
                    channel_data = json.loads(msg.value.decode('utf-8'))
                    
                    logger.debug(
                        f"Received channel event: {channel_data.get('id')}"
                    )
                    
                    # Создать dynamic consumer через Action
                    channel_id = await create_dynamic_consumer_action(
                        channel_data,
                        cache=self._cache,
                        manager=self._manager,
                        bootstrap_servers=self._bootstrap_servers
                    )
                    
                    if channel_id:
                        # Запустить ConsumerWorker для нового канала в фоне
                        worker = ConsumerWorker(
                            manager=self._manager,
                            channel_id=channel_id
                        )
                        
                        task = asyncio.create_task(worker.start())
                        
                        # Зарегистрировать task в менеджере для отслеживания
                        await self._manager.register_task(channel_id, task)
                        
                        logger.info(
                            f"Created and started worker for channel {channel_id}"
                        )
                
                except json.JSONDecodeError as exc:
                    logger.warning(
                        f"Failed to parse channel diff event: {exc}"
                    )
                    continue
                
                except Exception as exc:
                    logger.exception(
                        f"Error processing channel diff event: {exc}"
                    )
                    continue
        
        finally:
            await self._consumer.stop()
            logger.info("ChannelsDiffWorker stopped")
    
    async def stop(self):
        """
        Остановить worker gracefully.
        
        Устанавливает флаг _running = False и останавливает consumer.
        """
        logger.info("Stopping ChannelsDiffWorker")
        self._running = False
        
        if self._consumer:
            await self._consumer.stop()

