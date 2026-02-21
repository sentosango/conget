# Project: Conget

## Overview
Conget — простая CLI библиотека для получения веб-контента с плагинной архитектурой. Предоставляет несколько специализированных утилит-фетчеров, которые можно использовать как самостоятельно, так и через основную утилиту `conget` с автоматическим выбором фетчера. Также включает MCP сервер для интеграции с AI-агентами.

## Core Features

- **Множество фетчеров:**
  - `default` — универсальный фетчер для любых веб-страниц (trafilatura)
  - `github-repo` — README.md из GitHub репозиториев
  - `hh-vacancy` — вакансии с HH.ru через официальный API
  - `hh-employer` — информация о работодателях с HH.ru
- **Несколько форматов вывода:** html, markdown, text, json, xmltei, csv
- **Единая CLI:** `conget fetch/analyze/list/mcp` с автоматическим выбором фетчера
- **Специализированные CLI:** `conget-default`, `conget-github-repo`, `conget-hh-vacancy`, `conget-hh-employer`
- **MCP сервер:** интеграция с AI-агентами через Model Context Protocol (stdio transport)
- **Плагины сторонних разработчиков:** через Python entry-points
- **Централизованная конфигурация:** `~/.config/conget/config.toml` с автосозданием
- **Library API:** класс `Conget` для программного использования без CLI
- **Типизированные структуры:** dataclasses для типобезопасности

## Tech Stack

- **Language:** Python 3.12+
- **Installation:** `uv tool install .` (global CLI tools)
- **Dependency Manager:** uv
- **Package Manager:** pyproject.toml (hatchling build backend)
- **Content Extraction:** trafilatura
- **MCP Protocol:** mcp (stdio transport)
- **Config Format:** TOML (tomlkit for parsing)
- **HTTP Client:** requests (for API fetchers), trafilatura (for web fetchers)
- **HTML to Markdown:** markdownify

## Architecture Notes

### Плагинная архитектура через entry-points
- Все фетчеры регистрируются через `[project.entry-points."conget.fetchers"]` в pyproject.toml
- Автоматическая загрузка фетчеров из entry-points через `get_fetchers()`
- Специализированные фетчеры (is_special=True) имеют приоритет над универсальным

### Flat structure (минимум слоев)
- Один файл на фетчер в `src/fetchers/` без вложенных папок
- Каждая команда CLI в отдельном файле в `src/cli/`
- Модули в `src/core/` для переиспользуемой логики

### Базовый интерфейс BaseFetcher
Все фетчеры наследуют от `BaseFetcher`:
- **Свойство `metadata`:** `FetcherMetadata` с name, description, is_special, supported_formats, config_options
- **Метод `can_fetch(url)`:** проверяет, может ли фетчер обработать URL
- **Метод `fetch(url, format)`:** возвращает `FetchResult` с контентом и метаданными
- **Метод `run_cli()`:** стандартная CLI-обертка для фетчера

### Структура проекта
```
.                              # Project root
├── pyproject.toml             # Project config (metadata, dependencies, entry points)
├── src/
│   ├── conget.py               # Library API (класс Conget)
│   │
│   ├── cli/                   # Команды CLI
│   │   ├── main.py           # Диспетчер команд
│   │   ├── fetch.py          # Команда fetch + select_best_fetcher()
│   │   ├── list.py           # Команда list
│   │   ├── analyze.py        # Команда analyze
│   │   └── mcp.py           # MCP сервер
│   │
│   ├── core/                  # Базовые модули
│   │   ├── interfaces.py      # BaseFetcher абстрактный класс
│   │   ├── config.py         # Управление конфигурацией (~/.config/conget/)
│   │   ├── formatters.py     # Конвертация HTML -> Markdown -> Text
│   │   ├── types.py          # Typed dataclasses (FetcherMetadata, FetchResult, etc.)
│   │   ├── exceptions.py     # Иерархия исключений (CongetError, HTTPError, ...)
│   │   └── registry.py       # Загрузка фетчеров из entry-points
│   │
│   └── fetchers/             # Реализация фетчеров (flat structure)
│       ├── default.py         # DefaultFetcher + CLI
│       ├── github_repo.py     # GitHubRepoFetcher + CLI
│       ├── hh_vacancy.py     # HHVacancyFetcher + CLI
│       └── hh_employer.py    # HHEmployerFetcher + CLI
```

### Фетчеры

#### DefaultFetcher (trafilatura)
- Обрабатывает любые URL
- Форматы: html, markdown, text, xmltei, json, csv
- Опции конфигурации: include_comments, include_tables, include_images, include_formatting, include_links, with_metadata, no_ssl

#### GitHubRepoFetcher
- Обрабатывает GitHub репозитории (https://github.com/owner/repo)
- Форматы: markdown, text, json
- Фетчит README.md с main или master ветки
- Опции: prefer_branch (main/master)

#### HHVacancyFetcher
- Обрабатывает HH.ru вакансии (https://hh.ru/vacancy/123)
- Форматы: markdown, text, json
- Использует официальный API HH.ru
- Опции: timeout

#### HHEmployerFetcher
- Обрабатывает HH.ru работодателей (https://hh.ru/employer/123)
- Форматы: markdown, text, json
- Использует официальный API HH.ru
- Опции: timeout

### Exceptions
- `CongetError` — базовый класс для всех ошибок
- `HTTPError` — ошибки HTTP запросов (с status_code)
- `FetchError` — общие ошибки получения контента
- `ParsingError` — ошибки парсинга HTML/контента
- `UnsupportedFormatError` — неподдерживаемый формат (с output_format, supported)
- `ValidationError` — ошибки валидации URL/параметров
- `FetcherNotFoundError` — фетчер не найден
- `PluginLoadError` — ошибка загрузки плагина
- `TimeoutError` — таймаут операции

## Non-Functional Requirements

- **Logging:** Настраиваемый уровень (`--verbose`), по умолчанию WARNING
- **Error handling:** Иерархия исключений с контекстной информацией
- **Configuration:** Автоматическое создание config.toml при первом запуске с шаблоном опций
- **Type safety:** Typed structures (dataclasses) для всех данных
- **CLI UX:** Неявный fetch (URL без команды → fetch command), автопомощь при пустых аргументах
- **MCP Compatibility:** stdio transport для работы с Claude Code и другими MCP-клиентами
