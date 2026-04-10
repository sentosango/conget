# Conget

Простая CLI библиотека для получения веб-контента с плагинной архитектурой. Conget предоставляет несколько специализированных утилит для фетчинга контента из разных источников, а также MCP сервер для интеграции с AI-агентами.

## Возможности

- **Множество фетчеров:**
  - Универсальный фетчер для любых веб-страниц (trafilatura)
  - GitHub репозитории (README.md)
  - Вакансии с HH.ru
  - Информация о работодателях с HH.ru
  - Сериалы с MyShows.me

- **Несколько форматов вывода:** html, markdown, text, json, xmltei, csv

- **Единая CLI** с автоматическим выбором подходящего фетчера

- **MCP сервер** для интеграции с AI-агентами (Claude Code и др.)

- **Плагины сторонних разработчиков** через Python entry-points

- **Library API** для программного использования

## Установка

```bash
# Требуется uv (https://docs.astral.sh/uv/)
uv tool install .
```

## Использование

### Основная CLI

```bash
# Автоматический выбор фетчера по URL
conget https://example.com
conget https://github.com/user/repo
conget https://hh.ru/vacancy/123456
conget https://myshows.me/view/70013/
conget https://t.me/durov/352

# С указанием формата
conget https://example.com --format markdown
conget https://example.com --format json

# С указанием конкретного фетчера
conget https://example.com --fetcher default-trafilatura

# Подробный лог
conget https://example.com --verbose
```

#### Команды

```bash
# Получить контент
conget fetch <url> [--format <fmt>] [--fetcher <name>]

# Показать все доступные фетчеры
conget list [--format <fmt>]

# Проанализировать URL и показать подходящие фетчеры
conget analyze <url1> <url2> ...

# Запустить MCP сервер
conget mcp
```

### Специализированные CLI

Каждый фетчер имеет собственную CLI:

```bash
# Универсальный фетчер
conget-default-trafilatura https://example.com --format markdown

# GitHub репозитории
conget-github-repo https://github.com/user/repo

# HH вакансии
conget-hh-vacancy https://hh.ru/vacancy/123456

# HH работодатели
conget-hh-employer https://hh.ru/employer/123456

# MyShows сериалы
conget-myshows-show https://myshows.me/view/70013/

# MyShows фильмы
conget-myshows-movie https://myshows.me/movie/331468/

# Telegram посты
conget-telegram-post https://t.me/durov/352
```

### Library API

```python
from conget import Conget

conget = Conget()

# Получить контент
content = conget.fetch("https://example.com", format="markdown")

# Проанализировать URL
info = conget.analyze_url("https://github.com/user/repo")

# Список всех фетчеров
fetchers = conget.list_fetchers()

# Выбрать лучший фетчер для URL
fetcher_name = conget.select_fetcher("https://example.com")
```

### MCP сервер

Conget предоставляет MCP сервер для интеграции с AI-агентами. Настройте в `.mcp.json` или настройках MCP-клиента:

```json
{
  "conget": {
    "command": "conget",
    "args": ["mcp"]
  }
}
```

**Доступные инструменты:**
- `fetch` — получить контент с URL
- `analyze` — проанализировать URL и показать доступные фетчеры

## Конфигурация

Файл конфигурации создается автоматически при первом запуске:
```
~/.config/conget/config.toml
```

### Общие настройки

```toml
[general]
default_format = "markdown"  # Формат по умолчанию
```

### Настройки фетчеров

#### Default trafilatura fetcher

```toml
[default-trafilatura]
include_comments = true      # Включать комментарии
include_tables = true        # Включать таблицы
include_images = true        # Включать изображения
include_formatting = true   # Включать форматирование
include_links = true        # Включать ссылки
with_metadata = true        # Включать метаданные
no_ssl = false             # Отключить SSL проверку
```

#### GitHub fetcher

```toml
[github-repo]
prefer_branch = "main"      # Предпочитаемая ветка (main или master)
```

#### HH fetchers

```toml
[hh-vacancy]
timeout = 30               # Таймаут запросов (секунды)

[hh-employer]
timeout = 30               # Таймаут запросов (секунды)
```

#### MyShows fetcher

```toml
[myshows-show]
timeout = 30               # Таймаут запросов (секунды)
```

## Доступные форматы

| Формат | Описание | Поддержка по фетчерам |
|---------|-----------|----------------------|
| html | Исходный HTML | default-trafilatura |
| markdown | Markdown формат | default-trafilatura, github-repo, hh-vacancy, hh-employer, myshows-show, myshows-movie, telegram-post |
| text | Чистый текст без форматирования | default-trafilatura, github-repo, hh-vacancy, hh-employer, myshows-show, myshows-movie, telegram-post |
| json | JSON структура | default-trafilatura, github-repo, hh-vacancy, hh-employer, myshows-show, myshows-movie, telegram-post |
| xmltei | XML TEI формат | default-trafilatura |
| csv | CSV формат | default-trafilatura |

## Создание собственных фетчеров

```python
from src.core.interfaces import BaseFetcher
from src.core.types import FetcherMetadata, FetchResult

class MyFetcher(BaseFetcher):
    @property
    def metadata(self) -> FetcherMetadata:
        return FetcherMetadata(
            name="my-fetcher",
            description="Описание вашего фетчера",
            is_special=True,  # True для специализированных фетчеров
            supported_formats=["markdown", "text"],
        )

    def can_fetch(self, url: str) -> bool:
        # Проверьте, может ли фетчер обработать этот URL
        return "example.com" in url

    def fetch(self, url: str, output_format: str) -> FetchResult:
        # Получите контент
        content = "..."
        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
        )
```

Зарегистрируйте фетчер в `pyproject.toml`:

```toml
[project.entry-points."conget.fetchers"]
my-fetcher = "src.fetchers.my_fetcher:MyFetcher"
```

## Структура проекта

```
.                              # Project root
├── pyproject.toml             # Конфигурация проекта и entry-points
├── src/
│   ├── conget.py              # Library API
│   ├── cli/                   # Команды CLI
│   ├── core/                  # Базовые модули
│   └── fetchers/              # Реализации фетчеров
├── README.md
├── AGENTS.md
└── TODO.md
```

## Известные проблемы

### YouTube фетчеры

Фетчеры `youtube-video` и `youtube-playlist` возвращают контент на оригинальном языке, вне зависимости от указанной опции языка в конфигурации.

Это связано с ограничением библиотеки `yt-dlp`, которая используется для этих фетчеров. Опция остаётся в конфигурации в надежде на то, что проблема будет исправлена в будущих версиях yt-dlp.

Связанные ресурсы:
- [Issue в репозитории conget](https://github.com/sentosango/test_conget/issues/5)
- [Issue в репозитории yt-dlp](https://github.com/yt-dlp/yt-dlp/issues/13363)

## Лицензия

MIT

## Разработка

```bash
# Создать виртуальное окружение и установить зависимости
uv sync

# Запуск команд
uv run conget --help
uv run pytest
```

## Дополнительная информация

- Описание архитектуры: `.ai-factory/DESCRIPTION.md`
- Карта проекта: `AGENTS.md`
- Дорожная карта: `.ai-factory/ROADMAP.md`
- Идеи для новых фетчеров: `TODO.md`
