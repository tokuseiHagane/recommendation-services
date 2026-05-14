from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def get_project_root() -> Path:
    """
    Возвращает корень проекта, исходя из расположения этого файла:
    .../src/VkParser/config.py -> корень = parents[2]
    """
    return Path(__file__).resolve().parents[2]


def load_env() -> None:
    """
    Загружает переменные из .env, лежащего в корне проекта.
    """
    env_path = get_project_root() / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def get_vk_access_token() -> str:
    """
    Возвращает VK access token из окружения/.env.
    """
    load_env()

    token = os.getenv("VK_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "VK_ACCESS_TOKEN is not set. Put it into .env in the project root or export it in your environment."
        )

    return token
