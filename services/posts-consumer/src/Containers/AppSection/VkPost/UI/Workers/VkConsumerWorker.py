"""
VkConsumerWorker: Обработка VK постов из топика vk_posts_{group_id}.

Porto Architecture Worker:
- Основной worker для обработки VK постов
- Consume батч → Process → Manual commit
- Graceful shutdown support
"""

import asyncio
from typing import Any
import logging

from src.Containers.AppSection.VkPost.Tasks.ConsumeVkPostsBatchTask import consume_vk_posts_batch_task
from src.Containers.AppSection.VkPost.Actions.BatchProcessVkPostsAction import batch_process_vk_posts_action

logger = logging.getLogger(__name__)


class VkConsumerWorker:
    """
    Worker: Обработка VK постов из Kafka топика vk_posts_{group_id}.
    
    Workflow:
    1. Consume батч VK постов (ConsumeVkPostsBatchTask)
    2. Обработать батч (BatchProcessVkPostsAction)
    3. Manual commit offsets
    4. Повторить
    
    Graceful shutdown:
    - Устанавливает флаг _running = False
    - Завершает текущую итерацию
    - Возвращает управление
    
    Usage:
        worker = VkConsumerWorker(
            manager=manager,
            group_id=123,
            batch_size=100
        )
        await worker.start()  # Блокирующий вызов
        
        # В другой корутине для остановки:
        await worker.stop()
    """
    
    def __init__(
        self,
        manager: Any,  # VkDynamicConsumerManager
        group_id: int,
        batch_size: int = 100,
        batch_timeout_ms: int = 10000
    ):
        """
        Initialize VkConsumerWorker.
        
        Args:
            manager: VkDynamicConsumerManager instance
            group_id: ID VK группы для обработки
            batch_size: Максимальный размер батча
            batch_timeout_ms: Timeout для getmany (milliseconds)
        """
        self._manager = manager
        self._group_id = group_id
        self._batch_size = batch_size
        self._batch_timeout_ms = batch_timeout_ms
        self._running = False
        logger.info(f"VkConsumerWorker initialized for group {group_id}")
    
    async def start(self):
        """
        Запустить worker loop.
        
        Блокирующий вызов, работает до вызова stop().
        
        Raises:
            ValueError: Если консьюмер для группы не найден
        """
        self._running = True
        
        consumer = await self._manager.get_consumer(self._group_id)
        
        if not consumer:
            raise ValueError(
                f"No VK consumer found for group {self._group_id}"
            )
        
        logger.info(f"Starting VkConsumerWorker for group {self._group_id}")
        
        while self._running:
            try:
                # 1. Consume batch
                messages = await consume_vk_posts_batch_task(
                    consumer=consumer,
                    batch_size=self._batch_size,
                    timeout_ms=self._batch_timeout_ms
                )
                
                if not messages:
                    # Нет сообщений, продолжить
                    await asyncio.sleep(0.1)
                    continue
                
                # 2. Process batch через Action
                processed = await batch_process_vk_posts_action(
                    raw_posts=messages,
                    group_id=self._group_id
                )
                
                logger.debug(
                    f"Processed {processed} VK posts for group {self._group_id}"
                )
                
                # 3. Manual commit после успешной обработки
                if processed > 0:
                    await consumer.commit()
                    
                    logger.debug(
                        f"Committed offsets for VK group {self._group_id}"
                    )
                
            except asyncio.CancelledError:
                logger.info(
                    f"VkConsumerWorker for group {self._group_id} cancelled"
                )
                break
                
            except Exception as exc:
                logger.exception(
                    f"Error in VkConsumerWorker for group {self._group_id}: {exc}"
                )
                # Продолжить работу после ошибки с задержкой
                await asyncio.sleep(5)
        
        logger.info(f"VkConsumerWorker stopped for group {self._group_id}")
    
    async def stop(self):
        """
        Остановить worker gracefully.
        
        Устанавливает флаг _running = False, worker завершится после текущей итерации.
        """
        logger.info(f"Stopping VkConsumerWorker for group {self._group_id}")
        self._running = False
