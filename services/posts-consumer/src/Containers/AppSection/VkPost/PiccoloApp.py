"""
Piccolo App Configuration для VkPost контейнера.

Регистрирует все модели и миграции для VkPost.
Использует отдельную базу данных VK.
"""
import os
from piccolo.conf.apps import AppConfig

from src.Containers.AppSection.VkPost.Models.VkPost import VkPost
from src.Containers.AppSection.VkPost.Models.VkGroup import VkGroup

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="VkPost",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "migrations"
    ),
    table_classes=[VkPost, VkGroup],  # Явная регистрация моделей
    migration_dependencies=[],
    commands=[]
)
