---
name: plan
description: "Спланировать как реализовать указанную функцию Porto. Это второй шаг в жизненном цикле спецификационно-ориентированной разработки Porto."
---

Спланировать как реализовать указанную функцию Porto, используя технологический стек Litestar + Piccolo + Dishka + Logfire.

Это второй шаг в жизненном цикле спецификационно-ориентированной разработки Porto.

Учитывая детали реализации, предоставленные в качестве аргумента, выполни следующее:

1. **Настроить среду планирования**:
   ```bash
   # Создать скрипт настройки если он не существует
   mkdir -p scripts
   
   cat > scripts/setup-plan-porto.sh << 'EOF'
   #!/bin/bash
   # Find the current feature branch and spec
   BRANCH=$(git branch --show-current)
   FEATURE_SPEC="$(pwd)/specs/${BRANCH}/spec.md"
   IMPL_PLAN="$(pwd)/specs/${BRANCH}/plan.md"
   SPECS_DIR="$(pwd)/specs/${BRANCH}"
   
   # Copy the Porto plan template
   cp spec-kit/templates/plan-template-porto.md "$IMPL_PLAN"
   
   echo "{\"FEATURE_SPEC\":\"$FEATURE_SPEC\",\"IMPL_PLAN\":\"$IMPL_PLAN\",\"SPECS_DIR\":\"$SPECS_DIR\",\"BRANCH\":\"$BRANCH\"}"
   EOF
   chmod +x scripts/setup-plan-porto.sh
   
   # Run the setup
   ./scripts/setup-plan-porto.sh
   ```

2. **Разобрать JSON вывод** для путей FEATURE_SPEC, IMPL_PLAN, SPECS_DIR и BRANCH.

3. **Прочитать и проанализировать спецификацию функции Porto**:
   - Извлечь размещение Container (AppSection vs VendorSection)
   - Выявить требуемые Actions, Tasks, Models, UI компоненты
   - Понять бизнес-требования и пользовательские истории
   - Отметить любые взаимодействия или зависимости Container

4. **Прочитать конституцию Porto**:
   - Загрузить `spec-kit/memory/constitution-porto.md`
   - Понять архитектурные принципы Porto
   - Изучить требования к структуре Container
   - Отметить ограничения технологического стека (Litestar, Piccolo, Dishka, Logfire)

5. **Выполнить план реализации Porto**:
   - Загрузить шаблон плана из IMPL_PLAN
   - Установить входной путь к FEATURE_SPEC
   - Заполнить технический контекст деталями стека Porto:
     - Framework: Litestar 2.12+ (ASGI web framework)
     - ORM: Piccolo 1.22+ с SQLite/PostgreSQL
     - DI: Dishka 1.4+ (dependency injection)
     - Observability: Logfire 2.7+ (tracing, logging)
   - Включить предоставленные пользователем технические детали из аргументов: {ARGS}

6. **Проверка Porto Constitution**:
   - Проверить что размещение Container следует принципам Porto
   - Проверить соответствие паттерну Action-Task
   - Убедиться что переиспользование Ship компонентов запланировано
   - Валидировать подход к интеграции DI
   - Подтвердить стратегию наблюдаемости

7. **Выполнить фазы планирования**:
   
   **Фаза 0 - Исследование Porto** → `research.md`:
   - Исследовать существующие взаимодействия Container
   - Проанализировать нужные паттерны Piccolo ORM
   - Спланировать структуру Litestar controller
   - Спроектировать архитектуру Dishka provider
   - Спланировать стратегию интеграции Logfire
   
   **Фаза 1 - Дизайн Porto** → Множественные файлы:
   - `porto-structure.md`: Детальная разбивка Component
   - `data-model.md`: Схемы Piccolo model со связями
   - `contracts/`: Спецификации Litestar OpenAPI
   - `quickstart.md`: Специфичные для Porto тестовые сценарии
   
8. **Валидировать полноту планирования**:
   - Все компоненты Porto выявлены и запланированы
   - Структура Container следует соглашениям Porto
   - Интеграция Ship правильно спроектирована
   - DI providers правильно запланированы
   - Стратегия миграций базы данных определена

9. **Отчет о результатах** с:
   - Названием ветки и сгенерированными путями файлов
   - Стратегией реализации Container
   - Запланированными ключевыми компонентами Porto
   - Принятыми техническими решениями
   - Готовностью к команде `/tasks`

**Пример использования**:
```
/plan Использовать Piccolo ORM для моделей Order и OrderItem, создать OrderController в Litestar с REST endpoints, интегрировать с PaymentService в VendorSection, использовать Dishka для DI и Logfire для observability
```

**Соображения специфичные для Porto**:
- Всегда планируй для независимости Container
- Проектируй Actions как оркестраторы, Tasks как атомарные операции
- Планируй миграции Piccolo с самого начала
- Проектируй DTOs для границ API
- Планируй стратегию обработки исключений
- Учитывай влияние на производительность взаимодействий Container

Используй абсолютные пути для всех операций с файлами чтобы избежать проблем с путями. План должен быть немедленно действенным для команды `/tasks`.
