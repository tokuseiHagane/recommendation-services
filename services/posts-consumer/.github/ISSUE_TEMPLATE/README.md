# GitHub Issue Templates

Этот репозиторий использует современные **YAML Issue Forms** для структурированного создания issues.

## 📋 Доступные шаблоны

### 🐛 Bug Report (`bug-report.yml`)
- Для сообщения о багах и ошибках
- Включает специфичные поля для архитектуры Porto
- Автоматически добавляет метки: `bug`, `needs triage`

### ✨ Feature Request (`feature-request.yml`)
- Для предложения новых функций
- Подробная секция архитектурных компонентов Porto
- Автоматически добавляет метки: `enhancement`, `needs discussion`

### ❓ Question (`question.yml`)
- Для вопросов и предложений по документации
- Помогает классифицировать тип вопроса
- Автоматически добавляет метки: `question`, `documentation`

### 🏗️ Architecture (`architecture.yml`)
- Для серьезных архитектурных изменений
- Детальный анализ breaking changes
- Автоматически добавляет метки: `architecture`, `breaking change`, `needs discussion`

### ⚡ Performance (`performance.yml`)
- Для проблем производительности и оптимизаций
- Метрики и бенчмарки
- Автоматически добавляет метки: `performance`, `optimization`

### 🔒 Security (`security.yml`)
- Для некритических вопросов безопасности
- **ВНИМАНИЕ:** Не для критических уязвимостей!
- Автоматически добавляет метки: `security`, `needs review`

### 🤖 AI Task (`ai-task.yml`)
- Специальный шаблон для задач ИИ-разработки
- Подходит для автоматизированных процессов

## 🔧 Конфигурация

Файл `config.yml` содержит:
- Ссылки на документацию проекта
- Ссылки на внешние ресурсы (Litestar, Piccolo ORM, Dishka)
- Настройки для GitHub Issues

## 🏗️ Архитектура Porto

Все шаблоны адаптированы под архитектуру Porto и включают разделы для:

- **Containers**: AppSection, VendorSection
- **Ship Layer**: Core, Providers, Middleware, Commands
- **Business Logic**: Actions, Tasks, Models, Repositories
- **Infrastructure**: Litestar, Piccolo ORM, Dishka, FastStream, Logfire

## 📚 Полезные ссылки

- [Porto Architecture Documentation](../../../foxdocs/Porto-master/docs/)
- [Project Documentation](../../../docs/)
- [Litestar Documentation](https://docs.litestar.dev/)
- [Piccolo ORM Documentation](https://piccolo-orm.readthedocs.io/)
- [Dishka Documentation](https://dishka.readthedocs.io/)

## 🚨 Безопасность

Для критических уязвимостей безопасности **НЕ** используйте публичные issues. Вместо этого:
- Отправьте email на security@yourproject.com
- Используйте GitHub Security Advisories
- Свяжитесь с мейнтейнерами напрямую
