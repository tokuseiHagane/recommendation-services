#!/bin/bash

# Скрипт проверки предварительных требований задач Porto
# Проверяет какие документы дизайна доступны для генерации задач

set -e

# Получить текущую ветку
BRANCH=$(git branch --show-current)

if [ -z "$BRANCH" ] || [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "Ошибка: Не на ветке функции. Сначала используйте /specify и /plan."
    exit 1
fi

FEATURE_DIR="$(pwd)/specs/${BRANCH}"

if [ ! -d "$FEATURE_DIR" ]; then
    echo "Ошибка: Каталог функции не найден в $FEATURE_DIR"
    echo "Сначала запустите /specify и /plan."
    exit 1
fi

# Проверить какие документы доступны
AVAILABLE_DOCS=()

[[ -f "$FEATURE_DIR/plan.md" ]] && AVAILABLE_DOCS+=("plan.md")
[[ -f "$FEATURE_DIR/data-model.md" ]] && AVAILABLE_DOCS+=("data-model.md")
[[ -f "$FEATURE_DIR/porto-structure.md" ]] && AVAILABLE_DOCS+=("porto-structure.md")
[[ -f "$FEATURE_DIR/research.md" ]] && AVAILABLE_DOCS+=("research.md")
[[ -f "$FEATURE_DIR/quickstart.md" ]] && AVAILABLE_DOCS+=("quickstart.md")
[[ -d "$FEATURE_DIR/contracts" ]] && AVAILABLE_DOCS+=("contracts/")

# Проверить существует ли plan.md (обязательно)
if [ ! -f "$FEATURE_DIR/plan.md" ]; then
    echo "Ошибка: plan.md не найден. Сначала запустите /plan."
    exit 1
fi

# Преобразовать массив в формат JSON
DOCS_JSON="["
for i in "${!AVAILABLE_DOCS[@]}"; do
    if [ $i -gt 0 ]; then
        DOCS_JSON+=","
    fi
    DOCS_JSON+="\"${AVAILABLE_DOCS[$i]}\""
done
DOCS_JSON+="]"

# Вернуть JSON для разбора скриптом
echo "{\"FEATURE_DIR\":\"$FEATURE_DIR\",\"AVAILABLE_DOCS\":$DOCS_JSON,\"BRANCH\":\"$BRANCH\"}"
