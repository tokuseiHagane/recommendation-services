#!/bin/bash
# Docker entrypoint script for Distributed Monolith (TgPost / VkPost services)
# Автоматически применяет Piccolo миграции перед запуском приложения
# Supports SERVICE environment variable: "tg" (default) or "vk"

set -e

# Определить какой сервис запускаем
SERVICE=${SERVICE:-tg}

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Определить параметры в зависимости от сервиса
if [ "$SERVICE" = "vk" ]; then
    SERVICE_NAME="VkPost (VK)"
    PICCOLO_APP="VkPost"
    PICCOLO_CONF="piccolo_conf_vk"
    # Использовать VK_DB_* переменные если установлены
    export DB_HOST=${VK_DB_HOST:-${DB_HOST}}
    export DB_PORT=${VK_DB_PORT:-${DB_PORT}}
    export DB_USER=${VK_DB_USER:-${DB_USER}}
    export DB_PASSWORD=${VK_DB_PASSWORD:-${DB_PASSWORD}}
    export DB_NAME=${VK_DB_NAME:-${DB_NAME}}
else
    SERVICE_NAME="TgPost (Telegram)"
    PICCOLO_APP="TgPost"
    PICCOLO_CONF="piccolo_conf"
fi

echo -e "${BLUE}Starting $SERVICE_NAME service entrypoint...${NC}"

# Функция для ожидания готовности PostgreSQL
wait_for_postgres() {
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if python -c "
import asyncio
import asyncpg
import os

async def check():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        await conn.execute('SELECT 1')
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection attempt failed: {e}')
        return False

result = asyncio.run(check())
exit(0 if result else 1)
        " 2>/dev/null; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts - PostgreSQL not ready yet, waiting..."
        sleep 2
    done
    
    echo -e "${RED}PostgreSQL is not ready after $max_attempts attempts!${NC}"
    exit 1
}

# Функция для применения миграций
apply_migrations() {
    echo -e "${YELLOW}Checking Piccolo migrations for $PICCOLO_APP...${NC}"
    
    # Установить PICCOLO_CONF для использования правильного конфига
    export PICCOLO_CONF=$PICCOLO_CONF
    
    # Показать текущий статус миграций
    piccolo migrations check $PICCOLO_APP || true
    
    # Всегда запускаем forwards - Piccolo пропустит уже примененные
    echo -e "${YELLOW}Applying Piccolo migrations for $PICCOLO_APP...${NC}"
    
    if piccolo migrations forwards $PICCOLO_APP; then
        echo -e "${GREEN}Migrations applied successfully!${NC}"
    else
        echo -e "${RED}Failed to apply migrations!${NC}"
        exit 1
    fi
}

# Главная логика
main() {
    echo "================================================"
    echo "  $SERVICE_NAME - Piccolo Auto-Migration"
    echo "  Service: $SERVICE"
    echo "  Piccolo App: $PICCOLO_APP"
    echo "  Piccolo Conf: $PICCOLO_CONF"
    echo "  Database: $DB_NAME @ $DB_HOST:$DB_PORT"
    echo "================================================"
    echo ""
    
    # 1. Ждем готовности PostgreSQL
    wait_for_postgres
    
    # 2. Применяем миграции
    apply_migrations
    
    echo ""
    echo -e "${GREEN}Setup complete! Starting $SERVICE_NAME application...${NC}"
    echo "================================================"
    echo ""
    
    # 3. Запускаем приложение (передаем все аргументы скрипту)
    exec "$@"
}

# Запуск главной функции с передачей всех аргументов
main "$@"

