"""
Piccolo App Configuration для TgPost контейнера.

Регистрирует все модели и миграции для TgPost.
"""
import os
from piccolo.conf.apps import AppConfig

from src.Containers.AppSection.TgPost.Models.Post import Post

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="TgPost",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "migrations"
    ),
    table_classes=[Post],  # Явная регистрация моделей
    migration_dependencies=[],
    commands=[]
)


