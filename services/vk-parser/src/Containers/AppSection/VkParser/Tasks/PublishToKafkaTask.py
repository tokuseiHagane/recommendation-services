"""PublishToKafkaTask — publish groups and posts to Kafka topics."""

import json
from dataclasses import dataclass
from typing import Any

import logfire

from src.Containers.AppSection.VkParser.Data.Dto import KafkaGroupMessage, KafkaPostMessage
from src.Ship.Parents.Task import Task


@dataclass
class PublishToKafkaInput:
    groups: list[dict[str, Any]]
    posts: list[dict[str, Any]]
    kafka_bootstrap_servers: str
    kafka_groups_topic: str
    kafka_posts_topic_prefix: str


class PublishToKafkaTask(Task[PublishToKafkaInput, int]):
    """Publish parsed data to Kafka topics.

    - Groups go to ``vk_groups`` topic (one message per group).
    - Posts go to ``vk_posts_{group_id}`` topic (one message per post).

    Returns total number of messages published.
    """

    def __init__(self, producer: Any | None = None) -> None:
        self._producer = producer

    async def _ensure_producer(self, bootstrap_servers: str) -> Any:
        if self._producer is None:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            await self._producer.start()
        return self._producer

    async def run(self, data: PublishToKafkaInput) -> int:
        if not data.groups and not data.posts:
            return 0

        published = 0
        producer = self._producer
        owns_producer = False

        if producer is None:
            producer = await self._ensure_producer(data.kafka_bootstrap_servers)
            owns_producer = True

        try:
            for g in data.groups:
                group_id = g.get("id")
                if not group_id:
                    continue
                msg = KafkaGroupMessage(
                    id=group_id,
                    name=g.get("name"),
                    screen_name=g.get("screen_name"),
                    members_count=g.get("members_count"),
                )
                await producer.send_and_wait(
                    data.kafka_groups_topic,
                    msg.model_dump(mode="json"),
                )
                published += 1

            for p in data.posts:
                post_id = p.get("id")
                group_id = p.get("id_groups")
                if not post_id or not group_id:
                    continue
                msg = KafkaPostMessage(
                    id=post_id,
                    len_message=p.get("len_message"),
                    repost_count=p.get("repost_count", 0),
                    view_count=p.get("view_count", 0),
                    comments_count=p.get("comments_count", 0),
                    message_timestamp=p.get("message_timestamp"),
                    edit_date=p.get("edit_date"),
                    reactions_count=p.get("reactions_count", 0),
                    id_groups=group_id,
                )
                topic = f"{data.kafka_posts_topic_prefix}{group_id}"
                await producer.send_and_wait(topic, msg.model_dump(mode="json"))
                published += 1

        except Exception:
            logfire.error("Kafka publish error", exc_info=True)
            raise
        finally:
            if owns_producer:
                await producer.stop()
                self._producer = None

        logfire.info("Published to Kafka", groups=len(data.groups), posts_published=published)
        return published
