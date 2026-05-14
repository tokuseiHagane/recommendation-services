"""
VkDynamicConsumerManager Service: Управление динамическими Kafka консьюмерами для VK.

Porto Architecture Service:
- Создание и регистрация консьюмеров для VK групп
- Отслеживание активных консьюмеров
- Graceful shutdown всех консьюмеров
"""

from typing import Dict, Any, List, Optional
from aiokafka import AIOKafkaConsumer
import asyncio
import logging

try:
    import logfire
except ImportError:
    # Fallback если logfire не установлен
    class logfire:  # type: ignore
        @staticmethod
        def info(*args, **kwargs):
            pass
        
        @staticmethod
        def metric(*args, **kwargs):
            pass
        
        @staticmethod
        def warning(*args, **kwargs):
            pass
        
        @staticmethod
        def error(*args, **kwargs):
            pass

logger = logging.getLogger(__name__)


class VkDynamicConsumerManager:
    """
    Service: Управление динамическими Kafka консьюмерами для VK групп.
    
    Ответственность:
    - Создание и регистрация консьюмеров для топиков vk_posts_{group_id}
    - Отслеживание активных консьюмеров
    - Graceful shutdown всех консьюмеров
    - Предотвращение дубликатов консьюмеров
    
    Паттерн: Singleton (Dishka APP scope)
    
    Workflow:
    1. Инициализация: создание пустого менеджера
    2. Регистрация: добавление новых консьюмеров через add_consumer()
    3. Получение: доступ к консьюмерам через get_consumer()
    4. Shutdown: graceful остановка всех консьюмеров
    
    Usage:
        manager = VkDynamicConsumerManager(
            bootstrap_servers="localhost:9092",
            cache=cache
        )
        
        # Добавить консьюмер
        consumer = await create_kafka_consumer(group_id)
        success = await manager.add_consumer(group_id, consumer)
        
        # Получить консьюмер
        consumer = await manager.get_consumer(group_id)
        
        # Shutdown всех
        await manager.shutdown_all()
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        cache: Any  # VkGroupsCache
    ):
        """
        Initialize VkDynamicConsumerManager.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            cache: VkGroupsCache instance для синхронизации
        """
        self._consumers: Dict[int, AIOKafkaConsumer] = {}
        self._tasks: Dict[int, asyncio.Task] = {}
        self._bootstrap_servers = bootstrap_servers
        self._cache = cache
        self._lock = asyncio.Lock()
        logger.info(f"VkDynamicConsumerManager initialized with bootstrap: {bootstrap_servers}")
    
    async def add_consumer(
        self,
        group_id: int,
        consumer: AIOKafkaConsumer
    ) -> bool:
        """
        Добавить новый консьюмер в менеджер.
        
        Thread-safe операция через asyncio.Lock.
        
        Args:
            group_id: ID VK группы
            consumer: Запущенный AIOKafkaConsumer instance
            
        Returns:
            True если консьюмер добавлен, False если уже существует
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> consumer = AIOKafkaConsumer(...)
            >>> await consumer.start()
            >>> success = await manager.add_consumer(123, consumer)
            >>> success
            True
            >>> # Попытка добавить дубликат
            >>> await manager.add_consumer(123, consumer)
            False
        """
        async with self._lock:
            if group_id in self._consumers:
                logger.warning(
                    f"Consumer for VK group {group_id} already exists"
                )
                logfire.warning(
                    "Duplicate VK consumer attempt",
                    group_id=group_id
                )
                return False
            
            self._consumers[group_id] = consumer
            
            logger.info(f"Added consumer for VK group {group_id}")
            logfire.info(
                "VK Consumer added",
                group_id=group_id,
                total_consumers=len(self._consumers),
                active_consumers_count=len(self._consumers)
            )
            
            return True
    
    async def remove_consumer(self, group_id: int) -> bool:
        """
        Остановить и удалить консьюмер.
        
        Thread-safe операция через asyncio.Lock.
        
        Args:
            group_id: ID VK группы
            
        Returns:
            True если консьюмер удален, False если не существует
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> # ... добавить консьюмер ...
            >>> await manager.remove_consumer(123)
            True
        """
        async with self._lock:
            consumer = self._consumers.get(group_id)
            
            if not consumer:
                logger.warning(f"Consumer for VK group {group_id} not found")
                return False
            
            try:
                await consumer.stop()
                logger.info(f"Stopped consumer for VK group {group_id}")
            except Exception as exc:
                logger.error(
                    f"Error stopping consumer for VK group {group_id}: {exc}"
                )
                logfire.error(
                    "VK Consumer stop error",
                    group_id=group_id,
                    error=str(exc)
                )
            
            # Удалить из словаря
            del self._consumers[group_id]
            
            # Отменить task если есть
            task = self._tasks.pop(group_id, None)
            if task and not task.done():
                task.cancel()
            
            logger.info(f"Removed consumer for VK group {group_id}")
            logfire.info(
                "VK Consumer removed",
                group_id=group_id,
                total_consumers=len(self._consumers)
            )
            
            return True
    
    async def get_consumer(
        self,
        group_id: int
    ) -> Optional[AIOKafkaConsumer]:
        """
        Получить консьюмер по group_id.
        
        Args:
            group_id: ID VK группы
            
        Returns:
            AIOKafkaConsumer instance или None если не найден
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> consumer = await manager.get_consumer(123)
            >>> if consumer:
            ...     # работать с консьюмером
        """
        return self._consumers.get(group_id)
    
    async def get_all_consumers(self) -> Dict[int, AIOKafkaConsumer]:
        """
        Получить все активные консьюмеры.
        
        Returns:
            Dictionary {group_id: AIOKafkaConsumer}
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> consumers = await manager.get_all_consumers()
            >>> len(consumers)
            5
        """
        return self._consumers.copy()
    
    def get_all_consumer_ids(self) -> List[int]:
        """
        Получить список всех group IDs с активными консьюмерами.
        
        Returns:
            List of VK group IDs
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> ids = manager.get_all_consumer_ids()
            >>> ids
            [123, 456, 789]
        """
        return list(self._consumers.keys())
    
    async def shutdown_all(self):
        """
        Graceful shutdown всех консьюмеров.
        
        Останавливает все консьюмеры, отменяет все tasks, очищает словари.
        
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> # ... добавить консьюмеры ...
            >>> await manager.shutdown_all()
        """
        logger.info(f"Shutting down {len(self._consumers)} VK consumers")
        logfire.info(
            "VK Manager shutdown initiated",
            total_consumers=len(self._consumers)
        )
        
        async with self._lock:
            # Остановить все консьюмеры
            for group_id, consumer in self._consumers.items():
                try:
                    await consumer.stop()
                    logger.info(f"Stopped consumer for VK group {group_id}")
                except Exception as exc:
                    logger.error(
                        f"Failed to stop VK consumer {group_id}: {exc}"
                    )
                    logfire.error(
                        "VK Consumer stop error during shutdown",
                        group_id=group_id,
                        error=str(exc)
                    )
            
            # Отменить все tasks
            for group_id, task in self._tasks.items():
                if not task.done():
                    task.cancel()
                    logger.debug(f"Cancelled task for VK group {group_id}")
            
            # Очистить словари
            self._consumers.clear()
            self._tasks.clear()
            
            logger.info("All VK consumers shut down")
            logfire.info(
                "VK Manager shutdown completed",
                active_consumers_count=0
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику менеджера.
        
        Returns:
            Dictionary with manager stats:
            - total_consumers: int
            - active_tasks: int
            - consumer_ids: List[int]
            - bootstrap_servers: str
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> stats = await manager.get_stats()
            >>> stats["total_consumers"]
            5
        """
        return {
            "total_consumers": len(self._consumers),
            "active_tasks": len(self._tasks),
            "consumer_ids": list(self._consumers.keys()),
            "bootstrap_servers": self._bootstrap_servers
        }
    
    async def register_task(
        self,
        group_id: int,
        task: asyncio.Task
    ):
        """
        Зарегистрировать asyncio.Task для консьюмера.
        
        Используется для отслеживания worker tasks.
        
        Args:
            group_id: ID VK группы
            task: asyncio.Task instance
            
        Example:
            >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
            >>> task = asyncio.create_task(worker.start())
            >>> await manager.register_task(123, task)
        """
        self._tasks[group_id] = task
        logger.debug(f"Registered task for VK group {group_id}")
