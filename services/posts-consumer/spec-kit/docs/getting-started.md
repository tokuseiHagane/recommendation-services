# 🚀 Начало работы с Porto Spec Kit

Пошаговое руководство по началу работы с Porto Spec Kit в проекте с архитектурой Porto.

## 📋 Предварительные требования

### ✅ Технические требования
- **Python 3.11+** или выше
- **Git** для контроля версий
- **Проект Porto** с технологическим стеком Litestar + Piccolo + Dishka + Logfire

### 🤖 ИИ-агенты (опционально)
- **Claude Code** (рекомендуется)
- **GitHub Copilot** 
- **Gemini CLI**

### 📚 Необходимые знания
- Основы **архитектуры Porto** (Containers, Ship, Actions, Tasks)
- **Litestar** для создания API
- **Piccolo ORM** для работы с базой данных
- **Dishka** для внедрения зависимостей (dependency injection)

## 🎯 Быстрый старт (5 минут)

### 1. Проверьте структуру проекта
```bash
# Убедитесь что у вас есть Porto структура
ls src/
# Должно быть: Containers/ Ship/

ls src/Containers/
# Должно быть: AppSection/ VendorSection/
```

### 2. Инициализируйте Porto Spec Kit
```bash
# Создайте директории для спецификаций
mkdir -p specs

# Убедитесь что spec-kit присутствует
ls spec-kit/
# Должно быть: templates/ scripts/ docs/ memory/
```

### 3. Создайте первую фичу

**С ИИ-агентом (Claude Code, Copilot, etc.):**
```bash
/specify Система управления профилями пользователей с возможностью загрузки аватара
```

**Без ИИ (вручную):**
```bash
# Создайте новую фичу
./spec-kit/scripts/create-new-feature-porto.sh "Система управления профилями пользователей"

# Заполните спецификацию
# Откройте specs/001-sistema-upravleniya-profilyami/spec.md
```

### 4. Запланируйте реализацию

**С ИИ-агентом:**
```bash
/plan Использовать Piccolo для модели Profile, создать ProfileController в Litestar, добавить загрузку файлов через multipart/form-data
```

**Без ИИ (вручную):**
```bash
# Создайте план
./spec-kit/scripts/setup-plan-porto.sh

# Заполните план реализации
# Откройте specs/001-sistema-upravleniya-profilyami/plan.md
```

### 5. Сгенерируйте задачи

**С ИИ-агентом:**
```bash
/tasks
```

**Без ИИ (вручную):**
```bash
# Проверьте готовность к генерации задач
./spec-kit/scripts/check-task-prerequisites-porto.sh

# Создайте список задач
cp spec-kit/templates/tasks-template-porto.md specs/001-sistema-upravleniya-profilyami/tasks.md
```

## 📁 Структура после инициализации

```
your-porto-project/
├── src/                          # Исходный код Porto
│   ├── Containers/
│   │   ├── AppSection/
│   │   └── VendorSection/
│   └── Ship/
├── spec-kit/                     # Porto Spec Kit
│   ├── templates/               # Porto шаблоны
│   ├── scripts/                # Вспомогательные скрипты
│   ├── docs/                   # Документация
│   └── memory/                 # Конституция Porto
├── specs/                       # Спецификации фич
│   └── 001-feature-name/
│       ├── spec.md            # Спецификация
│       ├── plan.md            # План реализации
│       └── tasks.md           # Список задач
└── .cursor/                    # Настройки Cursor (если используется)
    └── rules
```

## 🎯 Первая фича: User Profile

Давайте создадим полную фичу управления профилями пользователей как пример.

### Шаг 1: Спецификация

Создайте спецификацию с основными требованиями:

```markdown
# Feature Specification: User Profile Management

**Porto Container**: AppSection.User
**Status**: Draft

## User Scenarios & Testing

### Primary User Story
Как пользователь, я хочу управлять своим профилем: просматривать, редактировать информацию и загружать аватар.

### Acceptance Scenarios (Porto Actions)
1. **Given** пользователь авторизован, **When** запрашивает профиль, **Then** получает свои данные
   - **Porto Action**: `GetUserProfileAction` in `AppSection.User`
   - **Expected Tasks**: `FindUserTask`, `TransformUserTask`

2. **Given** пользователь загружает аватар, **When** файл валиден, **Then** аватар сохраняется
   - **Porto Action**: `UpdateUserAvatarAction` in `AppSection.User`  
   - **Expected Tasks**: `ValidateImageTask`, `SaveFileTask`, `UpdateUserTask`
```

### Шаг 2: Планирование

```markdown
# Implementation Plan: User Profile Management (Porto)

**Porto Container**: AppSection.User (расширение существующего)

## Technical Context (Porto Stack)
**Framework**: Litestar 2.12+ (multipart file upload support)
**ORM**: Piccolo 1.22+ (User model extension)
**Storage**: Local filesystem for avatars
**Validation**: Pydantic for file validation

## Porto Constitution Check
- [x] Container placement: AppSection.User (core business logic)
- [x] Actions orchestrate: GetUserProfileAction → FindUserTask → TransformUserTask
- [x] File handling: SaveFileTask (reusable across containers)
```

### Шаг 3: Задачи

```markdown
# Tasks: User Profile Management (Porto)

## Phase 3.1: Extend User Model
- [ ] T001 Add avatar_url field to User model in `src/Containers/AppSection/User/Models/User.py`
- [ ] T002 Generate Piccolo migration: `piccolo migrations new user_avatar --auto`

## Phase 3.2: Profile Tasks
- [ ] T003 [P] Implement `ValidateImageTask` in `src/Containers/AppSection/User/Tasks/ValidateImage.py`
- [ ] T004 [P] Implement `SaveFileTask` in `src/Containers/AppSection/User/Tasks/SaveFile.py`
- [ ] T005 [P] Implement `UpdateUserAvatarTask` in `src/Containers/AppSection/User/Tasks/UpdateUserAvatar.py`

## Phase 3.3: Profile Actions
- [ ] T006 Implement `GetUserProfileAction` in `src/Containers/AppSection/User/Actions/GetUserProfile.py`
- [ ] T007 Implement `UpdateUserAvatarAction` in `src/Containers/AppSection/User/Actions/UpdateUserAvatar.py`

## Phase 3.4: API Layer
- [ ] T008 Add profile endpoints to `UserController`
- [ ] T009 Add file upload handling for avatar
- [ ] T010 Create `UserProfileDTO` for API responses
```

### Шаг 4: Реализация

Следуйте задачам и реализуйте компоненты:

```python
# src/Containers/AppSection/User/Tasks/ValidateImage.py
from src.Ship.Parents import Task
from PIL import Image
import io

class ValidateImageTask(Task[bytes, bool]):
    async def run(self, image_data: bytes) -> bool:
        try:
            image = Image.open(io.BytesIO(image_data))
            # Валидация размера, формата и т.д.
            return image.size[0] <= 1024 and image.size[1] <= 1024
        except:
            return False
```

## 🔧 Настройка среды разработки

### VS Code / Cursor
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "files.associations": {
    "*.md": "markdown"
  },
  "emmet.includeLanguages": {
    "markdown": "html"
  }
}
```

### Git Hooks
```bash
# .git/hooks/pre-commit
#!/bin/bash
# Проверка Porto структуры перед коммитом
if [[ $(git diff --cached --name-only) == *"src/Containers"* ]]; then
    echo "Checking Porto architecture compliance..."
    # Добавьте проверки структуры
fi
```

## 🧪 Тестирование

### Интеграционные тесты
```python
# tests/integration/test_user_profile_action.py
import pytest
from src.Containers.AppSection.User.Actions import GetUserProfileAction

@pytest.mark.asyncio
async def test_get_user_profile_action():
    # Тест полного потока Action → Task → Model
    pass
```

### E2E тесты
```python
# tests/e2e/test_user_profile_api.py
import pytest
from litestar.testing import TestClient

def test_get_user_profile_endpoint():
    with TestClient(app=app) as client:
        response = client.get("/users/profile")
        assert response.status_code == 200
```

## 📚 Следующие шаги

1. **Изучите примеры**: [Директория примеров](../examples/)
2. **Прочитайте документацию Porto**: [Документация Porto](../../docs/)
3. **Настройте Cursor**: [Правила Cursor](cursor-setup.md)
4. **Изучите лучшие практики**: [Лучшие практики](best-practices.md)

## 🆘 Получение помощи

- 📖 **Документация**: `spec-kit/docs/`
- 🎯 **Примеры**: `spec-kit/examples/`
- 🔧 **Шаблоны**: `spec-kit/templates/`
- 📜 **Конституция Porto**: `spec-kit/memory/constitution-porto.md`

---

🎉 **Поздравляем!** Вы готовы к использованию Porto Spec Kit для эффективной разработки с Porto архитектурой!
