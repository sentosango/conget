# Plan: CLI Options for Fetcher Config

**Feature:** Add `--options` JSON argument to pass fetcher-specific options via CLI
**Created:** 2026-02-22
**Mode:** Fast

## Settings
- **Testing:** No
- **Logging:** Minimal (WARN/ERROR only)
- **Docs:** No

## Overview

Currently, fetcher options (like `with_subs`, `lang`, `include_comments`) can only be configured via `~/.config/conget/config.toml`. Users want to override these options directly from CLI.

**Solution:** Add `--options` argument that accepts JSON:
```bash
conget-youtube-video "https://youtube.com/watch?v=xxx" --options '{"with_subs": false, "lang": "en"}'
conget fetch "https://youtube.com/watch?v=xxx" --options '{"with_subs": true}'
```

## Architecture

### Priority Chain
```
CLI --options > Config file > Metadata default
```

### Components to Modify

1. **`src/core/config.py`** — Add `merge_cli_options()` function
2. **`src/core/interfaces.py`** — Modify `run_cli()` to parse `--options` and pass to fetch
3. **`src/cli/fetch.py`** — Add `--options` argument to main fetch command
4. **`src/fetchers/*.py`** — Update fetchers to use merged options (youtube_video, default, etc.)

---

## Tasks

### Phase 1: Core Infrastructure

#### [x] Task 1: Add `merge_cli_options()` in config.py
**File:** `src/core/config.py`

Add function to merge CLI options with config:
```python
def merge_cli_options(
    fetcher_name: str,
    cli_options: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Merge CLI options with config file values.

    Priority: CLI > Config > Metadata default

    Args:
        fetcher_name: Fetcher name (e.g., 'youtube-video')
        cli_options: Options from --options JSON argument

    Returns:
        Merged options dict with final values
    """
```

Implementation:
1. Get config section via `get_section_config(fetcher_name)`
2. Load fetcher metadata to get defaults
3. Start with metadata defaults
4. Override with config values
5. Override with CLI options (if provided)
6. Return merged dict

**Logging:** WARN on invalid JSON, WARN on unknown option keys

---

#### [x] Task 2: Modify `BaseFetcher.run_cli()` to add --options
**File:** `src/core/interfaces.py`

Changes to `run_cli()`:
1. Add `--options` argument to argparse:
   ```python
   parser.add_argument(
       "--options",
       type=str,
       help='Fetcher options as JSON (e.g., \'{"with_subs": false}\')',
   )
   ```
2. Parse JSON with error handling
3. Use `merge_cli_options()` instead of direct `get_section_config()`
4. Pass merged options to a new `fetch_with_options()` method or modify fetch signature

**Important:** Need to modify how options flow to `fetch()` method. Options pattern:
- Add `fetch_options: Dict[str, Any] | None = None` parameter to `fetch()` signature
- Or add `set_options()` method to BaseFetcher
- Or pass via `fetch_with_cache()` and store in instance

**Logging:** WARN on JSON parse error

---

#### [x] Task 3: Add --options to main fetch command
**File:** `src/cli/fetch.py`

Changes to `run()`:
1. Add `--options` argument in `main.py` subparser setup
2. Pass `args.options` to fetcher
3. Use `merge_cli_options()` before calling `fetch_with_cache()`

---

### Phase 2: Update Fetchers

#### [x] Task 4: Update YoutubeVideoFetcher to use merged options
**File:** `src/fetchers/youtube_video.py`

Changes:
1. Modify `fetch()` to accept `fetch_options` parameter
2. Replace manual config reading with using passed options:
   ```python
   def fetch(self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None) -> FetchResult:
       options = fetch_options or {}
       lang = options.get("lang", self.metadata.config_options["lang"].default)
       with_subs = options.get("with_subs", self.metadata.config_options["with_subs"].default)
   ```
3. Update `fetch_with_cache()` to use passed options for cache key

---

#### [x] Task 5: Update DefaultFetcher to use merged options
**File:** `src/fetchers/default.py`

Same pattern as Task 4:
1. Add `fetch_options` parameter to `fetch()`
2. Use passed options instead of reading config directly

---

#### [x] Task 6: Update remaining fetchers
**Files:**
- `src/fetchers/github_repo.py`
- `src/fetchers/hh_vacancy.py`
- `src/fetchers/hh_employer.py`
- `src/fetchers/youtube_playlist.py`

Apply same pattern if they use config options.

---

### Phase 3: CLI & MCP Display Updates

#### [x] Task 8: Show config_options in conget list
**File:** `src/cli/list.py`

For each fetcher, after showing formats, also show available options:
```
  youtube-video [special]
    Description: Fetcher for YouTube video metadata
    Formats: markdown, text, json
    Options:
      lang: Language for metadata (default: "ru")
      with_subs: Include subtitles/transcript (default: true)
```

---

#### [x] Task 9: Show config_options in conget analyze
**File:** `src/cli/analyze.py`

Same pattern as Task 8 - show config_options for each matching fetcher.

---

#### [x] Task 10: Add options parameter to MCP fetch tool
**File:** `src/cli/mcp.py`

Changes:
1. Add `options` to fetch tool inputSchema:
   ```python
   "options": {
       "type": "object",
       "description": "Fetcher-specific options (e.g., {\"with_subs\": false})",
   }
   ```
2. In fetch_url_handler, use merge_cli_options() to merge with config
3. Pass merged options to fetch_with_cache()

---

#### [x] Task 11: Show config_options in MCP analyze tool
**File:** `src/cli/mcp.py`

In analyze_urls_handler, for each available fetcher also return config_options info.

---

### Phase 4: Cache & Fetcher Integration

#### [x] Task 7: Update cache key generation to use merged options
**File:** `src/core/interfaces.py`

Modify `fetch_with_cache()`:
1. Accept `fetch_options` parameter
2. Use merged options for cache key generation instead of reading from config

---

## Task Dependencies

```
#1 (merge_cli_options)
  ├── #2 (run_cli --options) → #7 (fetch_with_cache)
  │                              ├── #4 (YoutubeVideoFetcher)
  │                              ├── #5 (DefaultFetcher)
  │                              └── #6 (other fetchers)
  ├── #3 (fetch command --options)
  ├── #8 (list command - show options)
  ├── #9 (analyze command - show options)
  ├── #10 (MCP fetch - options param) [depends on #7]
  └── #11 (MCP analyze - show options)
```

**Execution Order:**
1. Task #1 - Foundation (merge_cli_options)
2. Tasks #2, #3, #8, #9, #11 - CLI/MCP display updates (parallel after #1)
3. Task #7 - Cache integration (after #2)
4. Tasks #4, #5, #6, #10 - Fetcher updates + MCP fetch (parallel after #7)

---

## Files Summary

| File | Changes |
|------|---------|
| `src/core/config.py` | Add `merge_cli_options()` |
| `src/core/interfaces.py` | Add `--options` to `run_cli()`, update `fetch_with_cache()` |
| `src/cli/main.py` | Add `--options` to fetch subparser |
| `src/cli/fetch.py` | Pass options to fetcher |
| `src/cli/list.py` | Show config_options for each fetcher |
| `src/cli/analyze.py` | Show config_options in analysis output |
| `src/cli/mcp.py` | Add `options` param to fetch tool, show options in analyze |
| `src/fetchers/youtube_video.py` | Use merged options |
| `src/fetchers/default.py` | Use merged options |
| `src/fetchers/github_repo.py` | Use merged options (if has config_options) |
| `src/fetchers/hh_vacancy.py` | Use merged options (if has config_options) |
| `src/fetchers/hh_employer.py` | Use merged options (if has config_options) |
| `src/fetchers/youtube_playlist.py` | Use merged options |

## Usage Examples

```bash
# Override with_subs via CLI
conget-youtube-video "https://youtube.com/watch?v=dQw4w9WgXcQ" --options '{"with_subs": false}'

# Multiple options
conget-youtube-video "https://youtube.com/watch?v=dQw4w9WgXcQ" --options '{"with_subs": true, "lang": "en"}'

# Main fetch command
conget fetch "https://youtube.com/watch?v=dQw4w9WgXcQ" --options '{"with_subs": false}'

# Default fetcher options
conget-default "https://example.com" --options '{"include_comments": false, "include_tables": true}'
```
