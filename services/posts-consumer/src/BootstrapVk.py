"""
BootstrapVk: Entry point для VkPost сервиса (VK).

Distributed Monolith: VK Posts Service

Запускает:
1. InitializeVkConsumersAction - создание консьюмеров для существующих VK групп
2. VkGroupsDiffWorker - прослушивание vk_groups_diff
3. VkConsumerWorkers - обработка постов для каждой группы
"""

import asyncio
import logging
import sys
import signal
import os

from dishka import make_async_container

from src.Containers.AppSection.VkPost.Providers import VkPostProvider
from src.Containers.AppSection.VkPost.Services.VkGroupsCache import VkGroupsCache
from src.Containers.AppSection.VkPost.Services.VkDynamicConsumerManager import VkDynamicConsumerManager
from src.Containers.AppSection.VkPost.Config.container_settings import container_settings
from src.Containers.AppSection.VkPost.Actions.InitializeVkConsumersAction import initialize_vk_consumers_action
from src.Containers.AppSection.VkPost.UI.Workers.VkGroupsDiffWorker import VkGroupsDiffWorker
from src.Containers.AppSection.VkPost.UI.Workers.VkConsumerWorker import VkConsumerWorker
from src.Containers.AppSection.VkPost.Tasks.InitializeVkDatabaseTask import initialize_vk_database_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def bootstrap_vk_post_service():
    """
    Bootstrap VkPost (VK) service.
    
    Workflow:
    1. Настроить Dishka container
    2. Получить сервисы (cache, manager)
    3. Инициализировать консьюмеры для существующих VK групп
    4. Запустить VkConsumerWorkers для каждой группы
    5. Запустить VkGroupsDiffWorker для прослушивания новых групп
    6. Ждать SIGTERM/SIGINT для graceful shutdown
    """
    
    logger.info("Starting VkPost (VK) service...")
    
    # 1. Настроить Dishka container
    container = make_async_container(VkPostProvider())
    
    try:
        # 2. Инициализировать VK БД (grants и настройки)
        logger.info("Initializing VK database...")
        await initialize_vk_database_task()
        
        # 3. Получить сервисы
        async with container() as request_container:
            cache = await request_container.get(VkGroupsCache)
            manager = await request_container.get(VkDynamicConsumerManager)
            
            logger.info("VkPost services initialized (cache, manager)")
            
            # 4. Инициализировать консьюмеры для существующих VK групп
            logger.info("Initializing consumers for existing VK groups...")
            
            created_count = await initialize_vk_consumers_action(
                cache=cache,
                manager=manager,
                bootstrap_servers=container_settings.kafka_bootstrap_servers,
                topic_prefix=container_settings.kafka_posts_topic_prefix
            )
            
            logger.info(
                f"Initialized {created_count} consumers for existing VK groups"
            )
            
            # 5. Запустить VkConsumerWorkers для каждой группы
            consumer_ids = manager.get_all_consumer_ids()
            worker_tasks = []
            
            for group_id in consumer_ids:
                worker = VkConsumerWorker(
                    manager=manager,
                    group_id=group_id,
                    batch_size=container_settings.batch_size,
                    batch_timeout_ms=container_settings.batch_timeout_ms
                )
                
                task = asyncio.create_task(worker.start())
                worker_tasks.append(task)
                await manager.register_task(group_id, task)
                
                logger.info(f"Started VkConsumerWorker for VK group {group_id}")
            
            # 6. Запустить VkGroupsDiffWorker
            groups_diff_worker = VkGroupsDiffWorker(
                bootstrap_servers=container_settings.kafka_bootstrap_servers,
                cache=cache,
                manager=manager,
                groups_diff_topic=container_settings.kafka_groups_diff_topic,
                topic_prefix=container_settings.kafka_posts_topic_prefix
            )
            
            groups_diff_task = asyncio.create_task(groups_diff_worker.start())
            
            logger.info("Started VkGroupsDiffWorker for VK")
            
            # 7. Настроить graceful shutdown
            shutdown_event = asyncio.Event()
            
            def signal_handler(sig, frame):
                logger.info(f"Received signal {sig}, initiating VkPost shutdown...")
                shutdown_event.set()
            
            # Регистрация signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, signal_handler)
            
            logger.info("VkPost (VK) service started successfully!")
            logger.info("Service is running, press Ctrl+C to stop...")
            
            # Ждать shutdown signal
            await shutdown_event.wait()
            
            # Graceful shutdown
            logger.info("Shutting down VkPost service...")
            
            # Остановить VkGroupsDiffWorker
            await groups_diff_worker.stop()
            groups_diff_task.cancel()
            
            try:
                await groups_diff_task
            except asyncio.CancelledError:
                pass
            
            logger.info("VkGroupsDiffWorker stopped")
            
            # Остановить все консьюмеры и workers
            await manager.shutdown_all()
            
            logger.info("All VK consumers and workers stopped")
            
            # Очистить кэш
            await cache.clear()
            
            logger.info("VkPost cache cleared")
    
    finally:
        await container.close()
        logger.info("VkPost (VK) service shut down successfully")


def main():
    """
    Main entry point for VkPost service.
    """
    try:
        asyncio.run(bootstrap_vk_post_service())
    except KeyboardInterrupt:
        logger.info("VkPost service interrupted by user")
    except Exception as exc:
        logger.exception(f"VkPost fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
