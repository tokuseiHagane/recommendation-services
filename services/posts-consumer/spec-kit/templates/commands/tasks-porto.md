---
name: tasks
description: "Разбить план Porto на исполняемые задачи. Это третий шаг в жизненном цикле спецификационно-ориентированной разработки Porto."
---

Разбить план Porto на исполняемые задачи, следуя паттернам архитектуры Porto.

Это третий шаг в жизненном цикле спецификационно-ориентированной разработки Porto.

Учитывая контекст, предоставленный в качестве аргумента, выполни следующее:

1. **Настроить среду задач**:
   ```bash
   # Создать скрипт предварительных требований задач если нужно
   mkdir -p scripts
   
   cat > scripts/check-task-prerequisites-porto.sh << 'EOF'
   #!/bin/bash
   BRANCH=$(git branch --show-current)
   FEATURE_DIR="$(pwd)/specs/${BRANCH}"
   
   # Check what documents are available
   AVAILABLE_DOCS=()
   [[ -f "$FEATURE_DIR/plan.md" ]] && AVAILABLE_DOCS+=("plan.md")
   [[ -f "$FEATURE_DIR/data-model.md" ]] && AVAILABLE_DOCS+=("data-model.md")
   [[ -f "$FEATURE_DIR/porto-structure.md" ]] && AVAILABLE_DOCS+=("porto-structure.md")
   [[ -f "$FEATURE_DIR/research.md" ]] && AVAILABLE_DOCS+=("research.md")
   [[ -f "$FEATURE_DIR/quickstart.md" ]] && AVAILABLE_DOCS+=("quickstart.md")
   [[ -d "$FEATURE_DIR/contracts" ]] && AVAILABLE_DOCS+=("contracts/")
   
   # Convert to JSON array
   DOCS_JSON=$(printf '%s\n' "${AVAILABLE_DOCS[@]}" | jq -R . | jq -s .)
   
   echo "{\"FEATURE_DIR\":\"$FEATURE_DIR\",\"AVAILABLE_DOCS\":$DOCS_JSON}"
   EOF
   chmod +x scripts/check-task-prerequisites-porto.sh
   
   # Run the check
   ./scripts/check-task-prerequisites-porto.sh
   ```

2. **Parse JSON output** for FEATURE_DIR and AVAILABLE_DOCS list.

3. **Load and analyze available Porto design documents**:
   - **ALWAYS read**: `plan.md` for Container placement and tech stack
   - **IF EXISTS**: `porto-structure.md` for detailed Component breakdown
   - **IF EXISTS**: `data-model.md` for Piccolo model specifications
   - **IF EXISTS**: `contracts/` for Litestar API endpoints
   - **IF EXISTS**: `research.md` for technical decisions
   - **IF EXISTS**: `quickstart.md` for test scenarios

4. **Сгенерировать специфичные для Porto задачи** следуя структуре шаблона:
   - Использовать `spec-kit/templates/tasks-template-porto.md` как основу
   - Заменить примеры задач на актуальные задачи Porto на основе анализа

5. **Правила генерации задач Porto**:
   
   **Задачи настройки Container**:
   - Создание структуры директорий Container
   - Конфигурация PiccoloApp.py
   - Настройка Dishka Providers.py
   - Файлы __init__.py для правильных импортов
   
   **Задачи Model [P]** (Параллельно - разные файлы):
   - Одна задача на Piccolo model из data-model.md
   - Задачи генерации миграций
   - Настройка валидации Model и связей
   
   **Реализация Task [P]** (Параллельно - разные файлы):
   - Одна задача на выявленную атомарную операцию
   - Расширение базового класса Ship.Parents.Task
   - Паттерны Repository если нужны
   
   **Реализация Action** (Последовательно - логика оркестрации):
   - Одна задача на бизнес use case
   - Расширение базового класса Ship.Parents.Action
   - Координация множественных Tasks
   
   **Задачи UI Layer**:
   - Litestar Controllers (из contracts/)
   - Регистрация API Routes
   - Классы DTO и Transformer
   - CLI команды если нужны
   
   **Задачи интеграции**:
   - Регистрация Dishka DI provider
   - Интеграция Ship компонентов
   - Настройка трассировки Logfire
   - Выполнение миграций базы данных

6. **Применить зависимости и порядок Porto**:
   - **Настройка** перед всем
   - **Models** перед Tasks перед Actions перед UI
   - **Тесты** параллельно с реализацией (TDD)
   - **Интеграция Ship** после основных компонентов
   - **Разные файлы** = могут быть параллельными [P]
   - **Тот же файл или зависимости** = последовательно (без [P])

7. **Сгенерировать специфичные для Porto пути файлов**:
   ```
   Container: src/Containers/[Section]/[ContainerName]/
   ├── Actions/[Action]Action.py
   ├── Tasks/[Task]Task.py
   ├── Models/[Model].py
   ├── UI/API/Controllers/[Controller].py
   ├── Data/[DTO].py
   ├── migrations/[timestamp]_[description].py
   ├── PiccoloApp.py
   └── Providers.py
   ```

8. **Создать tasks.md** в FEATURE_DIR с:
   - Правильным Porto Container и названием функции
   - Пронумерованными задачами (T001, T002, и т.д.)
   - Точными путями файлов Porto для каждой задачи
   - Заметками о зависимостях Porto
   - Руководством по параллельному выполнению для компонентов Porto
   - Принуждением TDD (тесты перед реализацией)

9. **Валидация задач Porto**:
   - Все Piccolo models имеют миграции?
   - Все компоненты имеют Dishka DI providers?
   - Все Actions имеют соответствующие Litestar controllers?
   - Ship Parents правильно расширены?
   - Интеграция Logfire запланирована?

10. **Сгенерировать примеры параллельного выполнения Porto**:
    ```bash
    # Пример: Модели можно создавать параллельно
    Task: "Создать модель User в src/Containers/AppSection/User/Models/User.py"
    Task: "Создать модель Profile в src/Containers/AppSection/User/Models/Profile.py"
    
    # Пример: Tasks можно реализовывать параллельно
    Task: "Реализовать CreateUserTask в src/Containers/AppSection/User/Tasks/CreateUser.py"
    Task: "Реализовать FindUserTask в src/Containers/AppSection/User/Tasks/FindUser.py"
    ```

**Контекст для генерации задач**: {ARGS}

**Требования к задачам специфичным для Porto**:
- Каждая задача должна указывать точные пути файлов Porto
- Задачи должны следовать соглашениям именования Porto
- TDD должен быть принудительным (тесты перед реализацией)
- Интеграция Dishka DI должна быть включена
- Переиспользование Ship компонентов должно быть максимизировано
- Независимость Container должна поддерживаться

Сгенерированный tasks.md должен быть немедленно исполняемым разработчиками, знакомыми с архитектурой Porto, где каждая задача достаточно специфична для начала реализации без дополнительного контекста.
