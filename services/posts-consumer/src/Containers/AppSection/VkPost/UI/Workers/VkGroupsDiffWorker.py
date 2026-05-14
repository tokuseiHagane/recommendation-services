"""
VkGroupsDiffWorker: Прослушивание vk_groups_diff для создания VK консьюмеров.

Porto Architecture Worker:
- Прослушивает топик vk_groups_diff
- Создает новые консьюмеры через CreateDynamicVkConsumerAction
- Запускает VkConsumerWorker для новых групп
"""

import asyncio
import json
from typing import Any
import logging

from aiokafka import AIOKafkaConsumer

from src.Containers.AppSection.VkPost.Actions.CreateDynamicVkConsumerAction import create_dynamic_vk_consumer_action
from src.Containers.AppSection.VkPost.UI.Workers.VkConsumerWorker import VkConsumerWorker

logger = logging.getLogger(__name__)


class VkGroupsDiffWorker:
    """
    Worker: Прослушивание vk_groups_diff для реактивного создания VK консьюмеров.
    
    Workflow:
    1. Consume события о новых VK группах из vk_groups_diff
    2. Создать новый консьюмер (CreateDynamicVkConsumerAction)
    3. Запустить VkConsumerWorker для новой группы
    
    Graceful shutdown:
    - Устанавливает флаг _running = False
    - Останавливает consumer
    - Возвращает управление
    
    Usage:
        worker = VkGroupsDiffWorker(
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
        cache: Any,  # VkGroupsCache
        manager: Any,  # VkDynamicConsumerManager
        groups_diff_topic: str = "vk_groups_diff",
        topic_prefix: str = "vk_posts_",
        consumer_group_id: str = "vk-groups-diff-consumer"
    ):
        """
        Initialize VkGroupsDiffWorker.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            cache: VkGroupsCache instance
            manager: VkDynamicConsumerManager instance
            groups_diff_topic: Топик для событий о группах
            topic_prefix: Префикс для топиков постов
            consumer_group_id: Consumer group ID
        """
        self._bootstrap_servers = bootstrap_servers
        self._cache = cache
        self._manager = manager
        self._groups_diff_topic = groups_diff_topic
        self._topic_prefix = topic_prefix
        self._consumer_group_id = consumer_group_id
        self._running = False
        self._consumer: Any = None  # AIOKafkaConsumer
        logger.info(f"VkGroupsDiffWorker initialized for topic {groups_diff_topic}")
    
    async def start(self):
        """
        Запустить worker loop.
        
        Блокирующий вызов, работает до вызова stop().
        Создает consumer для vk_groups_diff и обрабатывает события.
        """
        self._running = True
        
        # Создать consumer для vk_groups_diff
        self._consumer = AIOKafkaConsumer(
            self._groups_diff_topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._consumer_group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True  # Auto commit для упрощения
        )
        
        await self._consumer.start()
        
        logger.info(
            f"VkGroupsDiffWorker started, listening to {self._groups_diff_topic}"
        )
        
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                
                try:
                    # Parse group data
                    group_data = json.loads(msg.value.decode('utf-8'))

                    raw_group_id = group_data.get('id')
                    try:
                        group_id = int(raw_group_id) if raw_group_id is not None else None
                    except (TypeError, ValueError):
                        logger.warning(
                            "Received vk_groups_diff message with non-integer id=%r, skipping",
                            raw_group_id,
                        )
                        continue

                    if group_id is None:
                        logger.warning(
                            "Received vk_groups_diff message without id, skipping"
                        )
                        continue

                    # Ensure downstream consumers (cache/manager/action) see a normalized int
                    group_data["id"] = group_id

                    logger.debug(
                        f"Received VK group event: {group_id}"
                    )

                    # Short-circuit if manager already owns a consumer for this group.
                    # Without this check, a duplicate AIOKafkaConsumer could briefly
                    # join the same Kafka consumer group and trigger a rebalance loop.
                    existing = await self._manager.get_consumer(group_id)
                    if existing is not None:
                        logger.info(
                            "VK group %s already has a running consumer, skipping duplicate from diff",
                            group_id,
                        )
                        continue

                    # Создать dynamic consumer через Action
                    consumer = await create_dynamic_vk_consumer_action(
                        group_data=group_data,
                        cache=self._cache,
                        manager=self._manager,
                        bootstrap_servers=self._bootstrap_servers,
                        topic_prefix=self._topic_prefix
                    )

                    if consumer and group_id:
                        # Запустить VkConsumerWorker для новой группы в фоне
                        worker = VkConsumerWorker(
                            manager=self._manager,
                            group_id=group_id
                        )

                        task = asyncio.create_task(worker.start())

                        # Зарегистрировать task в менеджере для отслеживания
                        await self._manager.register_task(group_id, task)

                        logger.info(
                            f"Created and started VK worker for group {group_id}"
                        )
                
                except json.JSONDecodeError as exc:
                    logger.warning(
                        f"Failed to parse VK group diff event: {exc}"
                    )
                    continue
                
                except Exception as exc:
                    logger.exception(
                        f"Error processing VK group diff event: {exc}"
                    )
                    continue
        
        finally:
            await self._consumer.stop()
            logger.info("VkGroupsDiffWorker stopped")
    
    async def stop(self):
        """
        Остановить worker gracefully.
        
        Устанавливает флаг _running = False и останавливает consumer.
        """
        logger.info("Stopping VkGroupsDiffWorker")
        self._running = False
        
        if self._consumer:
            await self._consumer.stop()
