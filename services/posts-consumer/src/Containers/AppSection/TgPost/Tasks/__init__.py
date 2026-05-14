"""TgPost Tasks: Атомарные операции."""

from .BatchUpsertPostsTask import batch_upsert_posts_task
from .ValidatePostsTask import validate_posts_task
from .CreateKafkaConsumerTask import create_kafka_consumer_task
from .ConsumePostsBatchTask import consume_posts_batch_task
from .UpdateCacheTask import update_cache_task
from .CheckDuplicateTask import check_duplicate_task
from .RegisterConsumerTask import register_consumer_task
from .ValidateChannelDataTask import validate_channel_data_task
from .LoadChannelsFromDBTask import load_channels_from_db_task
from .InitializeDatabaseTask import initialize_database_task

__all__ = [
    "batch_upsert_posts_task",
    "validate_posts_task",
    "create_kafka_consumer_task",
    "consume_posts_batch_task",
    "update_cache_task",
    "check_duplicate_task",
    "register_consumer_task",
    "validate_channel_data_task",
    "load_channels_from_db_task",
    "initialize_database_task",
]
