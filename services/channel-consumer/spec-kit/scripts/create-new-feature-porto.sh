#!/bin/bash

# Скрипт создания функции Porto
# Создает новую ветку функции и структуру спецификации для архитектуры Porto

set -e

FEATURE_DESC="$1"

if [ -z "$FEATURE_DESC" ]; then
    echo "Ошибка: Требуется описание функции"
    echo "Использование: $0 'описание функции'"
    exit 1
fi

# Генерировать номер функции (следующий доступный)
FEATURE_NUM=$(printf "%03d" $(($(find specs -name "[0-9][0-9][0-9]-*" -type d 2>/dev/null | wc -l) + 1)))

# Генерировать слаг функции из описания
FEATURE_SLUG=$(echo "$FEATURE_DESC" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')

# Создать имя ветки
BRANCH_NAME="${FEATURE_NUM}-${FEATURE_SLUG}"

# Создать каталоги
SPEC_DIR="specs/${BRANCH_NAME}"
SPEC_FILE="${SPEC_DIR}/spec.md"

# Создать каталог спецификации
mkdir -p "$SPEC_DIR"

# Создать и переключиться на ветку
if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "Ветка $BRANCH_NAME уже существует, переключаюсь..."
    git checkout "$BRANCH_NAME"
else
    echo "Создаю новую ветку: $BRANCH_NAME"
    git checkout -b "$BRANCH_NAME"
fi

# Скопировать шаблон Porto спецификации, если он не существует
if [ ! -f "$SPEC_FILE" ]; then
    if [ -f "spec-kit/templates/spec-template-porto.md" ]; then
        cp "spec-kit/templates/spec-template-porto.md" "$SPEC_FILE"
        echo "Создан файл спецификации из шаблона Porto"
    else
        echo "Предупреждение: Шаблон Porto спецификации не найден, создаю базовый файл спецификации"
        cat > "$SPEC_FILE" << EOF
# Спецификация функции: $FEATURE_DESC

**Ветка функции**: \`$BRANCH_NAME\`
**Создано**: $(date +%Y-%m-%d)
**Статус**: Черновик
**Porto Container**: [AppSection/VendorSection].[НазваниеКонтейнера]

## Пользовательские сценарии и тестирование

### Основная пользовательская история
[Опишите основной пользовательский путь простым языком]

## Требования

### Функциональные требования (Porto компоненты)

#### Actions (Бизнес use cases)
- **FR-A001**: Система ДОЛЖНА предоставлять [НазваниеAction]Action для [возможности]

#### Tasks (Атомарные операции)
- **FR-T001**: Система ДОЛЖНА предоставлять [НазваниеTask]Task для [атомарной операции]

#### Models (Слой данных)
- **FR-M001**: Система ДОЛЖНА сохранять [НазваниеМодели] с [ключевыми атрибутами]

## Влияние на Porto архитектуру

### Требуемые новые компоненты
- **Container**: [Нужен новый контейнер? Или расширить существующий?]
- **Actions**: [Список Actions для создания]
- **Tasks**: [Список Tasks для создания] 
- **Models**: [Список Models для создания]
EOF
    fi
fi

# Вернуть JSON для разбора скриптом
echo "{\"BRANCH_NAME\":\"$BRANCH_NAME\",\"SPEC_FILE\":\"$(pwd)/$SPEC_FILE\",\"SPEC_DIR\":\"$(pwd)/$SPEC_DIR\"}"
