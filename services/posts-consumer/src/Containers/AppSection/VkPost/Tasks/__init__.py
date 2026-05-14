"""VkPost Tasks: Атомарные операции для VK данных."""

from src.Containers.AppSection.VkPost.Tasks.BatchUpsertVkPostsTask import batch_upsert_vk_posts_task
from src.Containers.AppSection.VkPost.Tasks.ValidateVkPostsTask import validate_vk_posts_task
from src.Containers.AppSection.VkPost.Tasks.LoadGroupsFromDBTask import load_groups_from_db_task
from src.Containers.AppSection.VkPost.Tasks.CreateKafkaConsumerTask import create_kafka_consumer_task
from src.Containers.AppSection.VkPost.Tasks.ConsumeVkPostsBatchTask import consume_vk_posts_batch_task
from src.Containers.AppSection.VkPost.Tasks.CheckDuplicateTask import check_duplicate_task
from src.Containers.AppSection.VkPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.VkPost.Tasks.RegisterConsumerTask import register_consumer_task
from src.Containers.AppSection.VkPost.Tasks.ValidateGroupDataTask import validate_group_data_task
from src.Containers.AppSection.VkPost.Tasks.InitializeVkDatabaseTask import initialize_vk_database_task

__all__ = [
    "batch_upsert_vk_posts_task",
    "validate_vk_posts_task",
    "load_groups_from_db_task",
    "create_kafka_consumer_task",
    "consume_vk_posts_batch_task",
    "check_duplicate_task",
    "update_cache_task",
    "register_consumer_task",
    "validate_group_data_task",
    "initialize_vk_database_task",
]
