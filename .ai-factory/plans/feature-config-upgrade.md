# Plan: Auto-upgrade Config with New Fetcher Options

## Overview
Реализовать механизм автоматического добавления новых опций фетчеров в конфигурационный файл пользователя через CLI команду.

**Branch:** feature/config-upgrade
**Created:** 2026-02-22

## Settings
- **Testing:** No
- **Logging:** Verbose (DEBUG level)
- **Docs:** No

## Problem
- Конфиг создаётся только при первом запуске (`init_config`)
- Новые фетчеры и их опции не добавляются в существующий конфиг
- `collect_fetcher_options()` хардкодит список фетчеров вместо использования registry

## Solution
1. Добавить функцию `upgrade_config()` в `src/core/config.py`
2. Рефакторинг `collect_fetcher_options()` для использования registry
3. Добавить CLI команду `conget config upgrade`

---

## Tasks

### Phase 1: Core Logic

#### - [x] Task 1: Refactor collect_fetcher_options() to use registry
**File:** `src/core/config.py`

Изменить функцию `collect_fetcher_options()` чтобы она загружала фетчеры динамически из entry-points через `get_fetchers()` из registry, а не хардкодила список.

**Logging:**
- DEBUG: начало загрузки фетчеров
- DEBUG: количество загруженных фетчеров
- WARNING: если фетчер не удалось загрузить

**Changes:**
```python
def collect_fetcher_options() -> Dict[str, Dict[str, Any]]:
    from src.core.registry import get_fetchers

    fetcher_classes = get_fetchers()
    options = {}

    for name, fetcher_cls in fetcher_classes.items():
        try:
            fetcher = fetcher_cls()
            options[fetcher.metadata.name] = fetcher.metadata.config_options
        except Exception as e:
            logger.warning(f"Failed to load fetcher {name}: {e}")

    return options
```

---

#### - [x] Task 2: Implement upgrade_config() function
**File:** `src/core/config.py`

Добавить функцию которая:
1. Загружает текущий конфиг пользователя
2. Получает опции всех фетчеров через `collect_fetcher_options()`
3. Для каждой секции фетчера проверяет наличие опций
4. Добавляет только те опции, которых нет в конфиге пользователя
5. Добавляет секции для новых фетчеров
6. Сохраняет обновлённый конфиг с сохранением комментариев

**Logging:**
- DEBUG: начало обновления конфига
- INFO: какие секции/опции добавлены
- DEBUG: путь к конфиг файлу

**Signature:**
```python
def upgrade_config() -> tuple[bool, list[str]]:
    """Upgrade config file with new fetcher options.

    Returns:
        Tuple of (was_upgraded, list of added items descriptions)
    """
```

---

### Phase 2: CLI Integration

#### - [x] Task 3: Add config upgrade CLI command
**File:** `src/cli/main.py`, `src/cli/config.py` (создан)

Добавить команду `config` (упрощена по требованию пользователя без подкоманд):

```
conget config    # Показать путь к конфигу и обновить новыми опциями
```

**Logging:**
- INFO: результат обновления (добавлено/конфиг актуален)
- DEBUG: список добавленных опций при --verbose

**CLI Output:**
```
$ conget config
Config: ~/.config/conget/config.toml
Already up to date
```

**Дополнительные изменения:**
- Использовать `platformdirs.user_config_dir` для консистентности с cache.py
- Вынести команду config в отдельный файл `src/cli/config.py` для консистентности с другими командами

---

## Commit Plan

После завершения всех задач — один коммит:

```
feat(config): add config upgrade command for new fetcher options

- Refactor collect_fetcher_options() to use registry instead of hardcoded list
- Add upgrade_config() function to merge new options into existing config
- Add 'conget config upgrade' CLI command
```

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/core/config.py` | Modify | Refactor + add upgrade_config() |
| `src/cli/main.py` | Modify | Add config upgrade command |

---

## Dependencies

```
Task 1 (registry refactor)
    ↓
Task 2 (upgrade_config)
    ↓
Task 3 (CLI command)
```
