"""Kafka Admin utilities for topic management."""

import logging
from typing import List, Dict, Any
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError
from src.Ship.config.settings import settings

logger = logging.getLogger(__name__)


def create_kafka_topics(
    topics: List[Dict[str, Any]],
    bootstrap_servers: str | None = None,
) -> bool:
    """
    Create Kafka topics if they don't exist.
    
    This function ensures required topics exist before the application starts consuming.
    It's safe to call even if topics already exist - it will skip existing topics.
    
    Args:
        topics: List of topic configurations, each with:
            - name (str): Topic name
            - num_partitions (int): Number of partitions (default: 1)
            - replication_factor (int): Replication factor (default: 1)
        bootstrap_servers: Kafka bootstrap servers (default: from settings)
    
    Returns:
        True if all topics were created or already exist, False on error
    
    Example:
        >>> topics = [
        ...     {"name": "tg_channels", "num_partitions": 3, "replication_factor": 1},
        ...     {"name": "tg_channels_diff", "num_partitions": 1, "replication_factor": 1},
        ... ]
        >>> create_kafka_topics(topics)
        True
    """
    if not bootstrap_servers:
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
    
    admin_client = None
    
    try:
        # Create admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id="tg-channel-consumer-admin",
            request_timeout_ms=10000,
        )
        
        # Get existing topics
        existing_topics = admin_client.list_topics()
        logger.info(f"Found {len(existing_topics)} existing topics in Kafka cluster")
        
        # Prepare topics to create
        topics_to_create = []
        for topic_config in topics:
            topic_name = topic_config["name"]
            
            if topic_name in existing_topics:
                logger.info(f"Topic '{topic_name}' already exists, skipping")
                continue
            
            # Create NewTopic object
            new_topic = NewTopic(
                name=topic_name,
                num_partitions=topic_config.get("num_partitions", 1),
                replication_factor=topic_config.get("replication_factor", 1),
            )
            topics_to_create.append(new_topic)
        
        # Create topics if needed
        if topics_to_create:
            logger.info(f"Creating {len(topics_to_create)} new topics...")
            
            result = admin_client.create_topics(
                new_topics=topics_to_create,
                validate_only=False,
                timeout_ms=10000,
            )
            
            # Check results
            for topic_name, future in result.items():
                try:
                    future.result()  # Blocks until topic creation completes
                    logger.info(f"✓ Topic '{topic_name}' created successfully")
                except TopicAlreadyExistsError:
                    logger.info(f"✓ Topic '{topic_name}' already exists")
                except KafkaError as e:
                    logger.error(f"✗ Failed to create topic '{topic_name}': {e}")
                    return False
        else:
            logger.info("All required topics already exist")
        
        return True
        
    except Exception as exc:
        logger.exception(f"Failed to create Kafka topics: {exc}")
        return False
        
    finally:
        if admin_client:
            admin_client.close()


def ensure_tg_topics() -> bool:
    """
    Ensure Telegram-related Kafka topics exist.
    
    Creates the following topics:
    - tg_channels: Main topic for incoming Telegram channel data
    - tg_channels_diff: Topic for publishing newly detected channels
    
    Returns:
        True if all topics were created or already exist, False on error
    """
    topics = [
        {
            "name": "tg_channels",
            "num_partitions": 3,  # Allow parallel processing
            "replication_factor": 1,  # Single broker setup
        },
        {
            "name": "tg_channels_diff",
            "num_partitions": 1,  # Sequential processing of diffs
            "replication_factor": 1,
        },
    ]
    
    logger.info("Ensuring Telegram Kafka topics exist...")
    return create_kafka_topics(topics)


def ensure_vk_topics() -> bool:
    """
    Ensure VK-related Kafka topics exist.
    
    Creates the following topics:
    - vk_groups: Main topic for incoming VK group data
    - vk_groups_diff: Topic for publishing newly detected groups
    
    Returns:
        True if all topics were created or already exist, False on error
    """
    topics = [
        {
            "name": "vk_groups",
            "num_partitions": 3,  # Allow parallel processing
            "replication_factor": 1,  # Single broker setup
        },
        {
            "name": "vk_groups_diff",
            "num_partitions": 1,  # Sequential processing of diffs
            "replication_factor": 1,
        },
    ]
    
    logger.info("Ensuring VK Kafka topics exist...")
    return create_kafka_topics(topics)


def ensure_application_topics() -> bool:
    """
    Ensure all application-required Kafka topics exist.
    
    Creates topics for both Telegram and VK modules based on settings.
    
    Returns:
        True if all topics were created or already exist, False on error
    """
    from src.Ship.config.settings import settings
    
    success = True
    
    if settings.ENABLE_TG_MODULE:
        success = ensure_tg_topics() and success
    
    if settings.ENABLE_VK_MODULE:
        success = ensure_vk_topics() and success
    
    return success

