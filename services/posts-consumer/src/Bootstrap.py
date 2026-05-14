"""
Bootstrap: Legacy entry point для обратной совместимости.

DEPRECATED: Используйте BootstrapTg.py или BootstrapVk.py напрямую.

Distributed Monolith:
- python -m src.BootstrapTg  # Telegram Posts Service
- python -m src.BootstrapVk  # VK Posts Service

Этот файл сохранен для обратной совместимости и запускает TgPost сервис.
"""

# Re-export from BootstrapTg for backward compatibility
from src.BootstrapTg import bootstrap_tg_post_service, main

if __name__ == "__main__":
    main()
