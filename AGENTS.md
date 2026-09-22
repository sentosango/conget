# AGENTS.md

> Project map for AI agents. Keep this file up-to-date as project evolves.

## Project Overview
**Conget** — простая CLI библиотека для получения веб-контента с плагинной архитектурой. Устанавливается через `uv tool install .`, предоставляет несколько CLI-утилит и MCP-сервер.

## Tech Stack
- **Language:** Python 3.12+
- **Installation:** `uv tool install .` from project root
- **Dependency Manager:** uv
- **Package Manager:** `conget/pyproject.toml` (hatchling build backend)
- **Content Extraction:** trafilatura (default-trafilatura fetcher)
- **MCP Protocol:** mcp (stdio transport)
- **Config Format:** TOML (tomlkit)
- **HTTP Client:** requests, trafilatura

## Project Structure

```
.                                   # Project root
├── README.md                       # User documentation
├── AGENTS.md                       # This file — project structure map
├── pyproject.toml                  # Project config (metadata, dependencies, entry points)
├── justfile                        # CLI installation commands and help
│
├── .ai-factory/                   # AI context
│   ├── DESCRIPTION.md               # Project specification
│   └── ROADMAP.md                 # Development roadmap
│
└── src/
        ├── __init__.py
        ├── conget.py               # Library API (class Conget)
        │
        ├── cli/                   # CLI commands
        │   ├── __init__.py
        │   ├── main.py            # Main entry point (dispatcher)
        │   ├── fetch.py           # conget fetch
        │   ├── list.py            # conget list
        │   ├── analyze.py         # conget analyze
        │   └── mcp.py             # conget mcp (MCP server)
        │
        ├── core/                  # Core modules
        │   ├── __init__.py
        │   ├── interfaces.py      # BaseFetcher interface
        │   ├── config.py         # Config handling (~/.config/conget/config.toml)
        │   ├── formatters.py     # Format handlers (HTML→Markdown→Text)
        │   ├── types.py          # Typed structures (dataclasses)
        │   ├── exceptions.py     # Exception hierarchy (CongetError, HTTPError, ...)
        │   └── registry.py      # Fetcher loader from entry-points
        │
        └── fetchers/            # Fetcher implementations (flat structure)
            ├── __init__.py
            ├── default_trafilatura.py  # DefaultTrafilaturaFetcher (trafilatura)
            ├── github_repo.py    # GitHubRepoFetcher
            ├── hh_vacancy.py    # HHVacancyFetcher
            ├── hh_employer.py   # HHEmployerFetcher
            └── telegram_post.py # TelegramPostFetcher
```

## Key Entry Points

| Entry Point | Purpose |
|-------------|---------|
| `conget` | Main CLI with commands: fetch/analyze/list/mcp |
| `conget-default-trafilatura` | Generic web content fetcher (trafilatura) |
| `conget-github-repo` | GitHub repository fetcher (README.md) |
| `conget-hh-vacancy` | HH.ru vacancy fetcher (via API) |
| `conget-hh-employer` | HH.ru employer fetcher (via API) |
| `conget-telegram-post` | Telegram public post fetcher |
| `conget-myshows-movie` | MyShows.me movie fetcher (HTML parsing) |
| `[project.entry-points."conget.fetchers"]` | Registration of third-party fetchers |

## Library API

Import `Conget` class from `conget` module for programmatic usage:

```python
from conget import Conget

conget = Conget()
content = conget.fetch("https://example.com", format="markdown")
info = conget.analyze_url("https://github.com/user/repo")
fetchers = conget.list_fetchers()
```

## Documentation
| Document | Path | Description |
|----------|------|-------------|
| README | README.md | Conget usage documentation |
| Description | .ai-factory/DESCRIPTION.md | Project specification and tech stack |
| Roadmap | .ai-factory/ROADMAP.md | Development roadmap |

## AI Context Files
| File | Purpose |
|------|---------|
| AGENTS.md | This file — project structure map |
| .ai-factory/DESCRIPTION.md | Project specification and tech stack |
| .ai-factory/ROADMAP.md | Development milestones |

## Key Patterns

### Fetcher Structure
- **Single file per fetcher:** Each fetcher is a single `.py` file in `fetchers/` directory
- **Flat structure:** No nested folders, all fetchers at same level
- **Implements BaseFetcher:** All fetchers inherit from `src.core.interfaces.BaseFetcher`
- **CLI integration:** Each fetcher has `if __name__ == "__main__"` block calling `cli()`

### CLI Structure
- **Separate command files:** Each command in `cli/<command>.py`
- **Main dispatcher:** `cli/main.py` routes to appropriate command
- **Implicit fetch:** URL as first argument triggers fetch command
- **Fetcher CLI:** Integrated directly in fetcher file via `cli()` method

### Plugin System
- **Entry-points:** Load fetchers dynamically via `[project.entry-points."conget.fetchers"]`
- **Auto-selection:** Specialized fetchers have priority over generic

### Typed Structures
- **Dataclasses:** All data structures use Python dataclasses for type safety
- **FetchResult:** Return type for all fetch operations
- **FetcherMetadata:** Contains fetcher information (name, description, formats, etc.)
- **Validation:** Built-in validation in `__post_init__` methods

## Development Guidelines

- **Minimum layers:** Fetcher implementation in a single file, no extra abstraction
- **Flat structure:** All fetchers in `src/fetchers/` without nested folders
- **Single config:** All settings in `~/.config/conget/config.toml`
- **Auto-creation:** Config file created on first run if missing
- **Exception hierarchy:** Use `CongetError` and its subclasses for error handling
- **Type safety:** Use typed structures (FetchResult, FetcherMetadata) for all data

## Adding New Fetchers

1. Create file `src/fetchers/<fetcher_name>.py` with `BaseFetcher` implementation
2. Add CLI block at end:
   ```python
   if __name__ == "__main__":
       MyFetcher.run_cli(url_help="Description of URL type")
   ```
3. Add entry-points in `pyproject.toml`:
   ```toml
   [project.scripts]
   conget-<name> = "src.fetchers.<fetcher_name>:cli"

   [project.entry-points."conget.fetchers"]
   <name> = "src.fetchers.<fetcher_name>:MyFetcher"
   ```
4. Optionally update `src/fetchers/__init__.py` to export new fetcher for direct imports
