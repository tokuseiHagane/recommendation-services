"""VK Group tasks."""
from src.Containers.vk_group.tasks.batch_upsert_groups_task import batch_upsert_groups_task
from src.Containers.vk_group.tasks.cache_groups_task import (
    cache_groups_task,
    get_cached_groups_task,
    clear_cache_task,
)
from src.Containers.vk_group.tasks.publish_from_cache_task import publish_from_cache_task

__all__ = [
    "batch_upsert_groups_task",
    "cache_groups_task",
    "get_cached_groups_task",
    "clear_cache_task",
    "publish_from_cache_task",
]
