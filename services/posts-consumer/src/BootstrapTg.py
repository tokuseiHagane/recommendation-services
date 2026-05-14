"""
BootstrapTg: Entry point для TgPost сервиса (Telegram).

Distributed Monolith: Telegram Posts Service

Запускает:
1. InitializeConsumersAction - создание консьюмеров для существующих каналов
2. ChannelsDiffWorker - прослушивание tg_channels_diff
3. ConsumerWorkers - обработка постов для каждого канала
"""

import asyncio
import logging
import sys
import signal
import os

from dishka import make_async_container

from src.Containers.AppSection.TgPost.Providers import TgPostProvider
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import PostObjectsCache
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import DynamicConsumerManager
from src.Containers.AppSection.TgPost.Config.container_settings import container_settings
from src.Containers.AppSection.TgPost.Actions.InitializeConsumersAction import initialize_consumers_action
from src.Containers.AppSection.TgPost.UI.Workers.ChannelsDiffWorker import ChannelsDiffWorker
from src.Containers.AppSection.TgPost.UI.Workers.ConsumerWorker import ConsumerWorker
from src.Containers.AppSection.TgPost.Tasks.InitializeDatabaseTask import initialize_database_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def bootstrap_tg_post_service():
    """
    Bootstrap TgPost (Telegram) service.
    
    Workflow:
    1. Настроить Dishka container
    2. Получить сервисы (cache, manager)
    3. Инициализировать консьюмеры для существующих каналов
    4. Запустить ConsumerWorkers для каждого канала
    5. Запустить ChannelsDiffWorker для прослушивания новых каналов
    6. Ждать SIGTERM/SIGINT для graceful shutdown
    """
    
    logger.info("Starting TgPost (Telegram) service...")
    
    # 1. Настроить Dishka container
    container = make_async_container(TgPostProvider())
    
    try:
        # 2. Инициализировать БД (grants и настройки)
        logger.info("Initializing Telegram database...")
        db_name = os.getenv("DB_NAME", "post_db")
        db_user = os.getenv("DB_USER", "app_user")
        await initialize_database_task(db_name=db_name, db_user=db_user)
        
        # 3. Получить сервисы
        async with container() as request_container:
            cache = await request_container.get(PostObjectsCache)
            manager = await request_container.get(DynamicConsumerManager)
            
            logger.info("TgPost services initialized (cache, manager)")
            
            # 4. Инициализировать консьюмеры для существующих каналов
            logger.info("Initializing consumers for existing Telegram channels...")
            
            created_count = await initialize_consumers_action(
                cache=cache,
                manager=manager,
                bootstrap_servers=container_settings.kafka_bootstrap_servers
            )
            
            logger.info(
                f"Initialized {created_count} consumers for existing Telegram channels"
            )
            
            # 5. Запустить ConsumerWorkers для каждого канала
            consumer_ids = manager.get_all_consumer_ids()
            worker_tasks = []
            
            for channel_id in consumer_ids:
                worker = ConsumerWorker(
                    manager=manager,
                    channel_id=channel_id,
                    batch_size=container_settings.batch_size,
                    batch_timeout_ms=container_settings.batch_timeout_ms
                )
                
                task = asyncio.create_task(worker.start())
                worker_tasks.append(task)
                await manager.register_task(channel_id, task)
                
                logger.info(f"Started ConsumerWorker for Telegram channel {channel_id}")
            
            # 6. Запустить ChannelsDiffWorker
            channels_diff_worker = ChannelsDiffWorker(
                bootstrap_servers=container_settings.kafka_bootstrap_servers,
                cache=cache,
                manager=manager
            )
            
            channels_diff_task = asyncio.create_task(channels_diff_worker.start())
            
            logger.info("Started ChannelsDiffWorker for Telegram")
            
            # 7. Настроить graceful shutdown
            shutdown_event = asyncio.Event()
            
            def signal_handler(sig, frame):
                logger.info(f"Received signal {sig}, initiating TgPost shutdown...")
                shutdown_event.set()
            
            # Регистрация signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, signal_handler)
            
            logger.info("TgPost (Telegram) service started successfully!")
            logger.info("Service is running, press Ctrl+C to stop...")
            
            # Ждать shutdown signal
            await shutdown_event.wait()
            
            # Graceful shutdown
            logger.info("Shutting down TgPost service...")
            
            # Остановить ChannelsDiffWorker
            await channels_diff_worker.stop()
            channels_diff_task.cancel()
            
            try:
                await channels_diff_task
            except asyncio.CancelledError:
                pass
            
            logger.info("ChannelsDiffWorker stopped")
            
            # Остановить все консьюмеры и workers
            await manager.shutdown_all()
            
            logger.info("All Telegram consumers and workers stopped")
            
            # Очистить кэш
            await cache.clear()
            
            logger.info("TgPost cache cleared")
    
    finally:
        await container.close()
        logger.info("TgPost (Telegram) service shut down successfully")


def main():
    """
    Main entry point for TgPost service.
    """
    try:
        asyncio.run(bootstrap_tg_post_service())
    except KeyboardInterrupt:
        logger.info("TgPost service interrupted by user")
    except Exception as exc:
        logger.exception(f"TgPost fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
