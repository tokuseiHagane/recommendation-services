"""
ConsumerWorker: Обработка постов из топика tg_posts_{id}.

Porto Architecture Worker:
- Основной worker для обработки постов
- Consume батч → Process → Manual commit
- Graceful shutdown support
"""

import asyncio
from typing import Any
import logging

from src.Containers.AppSection.TgPost.Tasks.ConsumePostsBatchTask import consume_posts_batch_task
from src.Containers.AppSection.TgPost.Actions.BatchProcessPostsAction import batch_process_posts_action

logger = logging.getLogger(__name__)


class ConsumerWorker:
    """
    Worker: Обработка постов из Kafka топика tg_posts_{id}.
    
    Workflow:
    1. Consume батч постов (ConsumePostsBatchTask)
    2. Обработать батч (BatchProcessPostsAction)
    3. Manual commit offsets
    4. Повторить
    
    Graceful shutdown:
    - Устанавливает флаг _running = False
    - Завершает текущую итерацию
    - Возвращает управление
    
    Usage:
        worker = ConsumerWorker(
            manager=manager,
            channel_id=123,
            batch_size=100
        )
        await worker.start()  # Блокирующий вызов
        
        # В другой корутине для остановки:
        await worker.stop()
    """
    
    def __init__(
        self,
        manager: Any,  # DynamicConsumerManager
        channel_id: int,
        batch_size: int = 100,
        batch_timeout_ms: int = 10000
    ):
        """
        Initialize ConsumerWorker.
        
        Args:
            manager: DynamicConsumerManager instance
            channel_id: ID канала для обработки
            batch_size: Максимальный размер батча
            batch_timeout_ms: Timeout для getmany (milliseconds)
        """
        self._manager = manager
        self._channel_id = channel_id
        self._batch_size = batch_size
        self._batch_timeout_ms = batch_timeout_ms
        self._running = False
        logger.info(f"ConsumerWorker initialized for channel {channel_id}")
    
    async def start(self):
        """
        Запустить worker loop.
        
        Блокирующий вызов, работает до вызова stop().
        
        Raises:
            ValueError: Если консьюмер для канала не найден
        """
        self._running = True
        
        consumer = await self._manager.get_consumer(self._channel_id)
        
        if not consumer:
            raise ValueError(
                f"No consumer found for channel {self._channel_id}"
            )
        
        logger.info(f"Starting ConsumerWorker for channel {self._channel_id}")
        
        while self._running:
            try:
                # 1. Consume batch
                messages = await consume_posts_batch_task(
                    consumer=consumer,
                    batch_size=self._batch_size,
                    timeout_ms=self._batch_timeout_ms
                )
                
                if not messages:
                    # Нет сообщений, продолжить
                    await asyncio.sleep(0.1)
                    continue
                
                # 2. Process batch через Action
                processed = await batch_process_posts_action(
                    raw_posts=messages,
                    channel_id=self._channel_id
                )
                
                logger.debug(
                    f"Processed {processed} posts for channel {self._channel_id}"
                )
                
                # 3. Manual commit после успешной обработки
                if processed > 0:
                    await consumer.commit()
                    
                    logger.debug(
                        f"Committed offsets for channel {self._channel_id}"
                    )
                
            except asyncio.CancelledError:
                logger.info(
                    f"ConsumerWorker for channel {self._channel_id} cancelled"
                )
                break
                
            except Exception as exc:
                logger.exception(
                    f"Error in ConsumerWorker for channel {self._channel_id}: {exc}"
                )
                # Продолжить работу после ошибки с задержкой
                await asyncio.sleep(5)
        
        logger.info(f"ConsumerWorker stopped for channel {self._channel_id}")
    
    async def stop(self):
        """
        Остановить worker gracefully.
        
        Устанавливает флаг _running = False, worker завершится после текущей итерации.
        """
        logger.info(f"Stopping ConsumerWorker for channel {self._channel_id}")
        self._running = False

