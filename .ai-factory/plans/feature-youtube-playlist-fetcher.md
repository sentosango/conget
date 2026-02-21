# Plan: YouTube Playlist Fetcher

**Branch:** feature/youtube-playlist-fetcher
**Created:** 2026-02-21

## Settings

- **Testing:** No
- **Logging:** Minimal (WARN/ERROR only)
- **Docs:** Yes (update DESCRIPTION.md)

## Description

Добавить новый фетчер `youtube-playlist` для извлечения метаданных YouTube плейлистов с использованием yt-dlp (без аутентификации, без скачивания видео).

## Tasks

### Phase 1: Implementation

- [ ] **Task #1**: Создать YoutubePlaylistFetcher в src/fetchers/youtube_playlist.py
  - Файл: `src/fetchers/youtube_playlist.py`
  - Класс YoutubePlaylistFetcher наследует BaseFetcher
  - URL patterns: youtube.com/playlist?list=PLAYLIST_ID (см. полный список в Implementation Notes)
  - Config options:
    - `lang` (default="ru") — язык метаданных
    - `with_list` (default=True) — включать ли список видео в вывод
  - Извлекаемые поля плейлиста: id, url, title, description, channel, channel_url, video_count, videos (список с id, title, url, duration для каждого видео, только если include_videos=True)
  - Форматы: markdown, text, json
  - yt-dlp options: quiet=True, no_warnings=True, extract_flat='in_playlist' (для быстрого получения списка без полной загрузки каждого видео), extractor_args={'youtube': {'lang': [lang]}}
  - Обработка ошибок: yt_dlp.DownloadError/ExtractorError → FetchError
  - Для text-формата использовать src.core.formatters.markdown_to_text()

### Phase 2: Registration

- [ ] **Task #2**: Зарегистрировать youtube-playlist в entry-points pyproject.toml
  - Файл: `pyproject.toml`
  - CLI script: conget-youtube-playlist
  - Entry-point: youtube-playlist

### Phase 3: Documentation

- [ ] **Task #3**: Обновить DESCRIPTION.md с новым фетчером
  - Файл: `.ai-factory/DESCRIPTION.md`
  - Зависит от: Task #1
  - Добавить описание YoutubePlaylistFetcher

## Implementation Notes

### yt-dlp Usage Pattern for Playlists

```python
from yt_dlp import YoutubeDL

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': 'in_playlist',  # Быстрое получение списка видео
    'extractor_args': {
        'youtube': {
            'lang': [lang],  # e.g., 'ru', 'en', 'de'
        },
    },
}
with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(playlist_url, download=False)
    info_dict = ydl.sanitize_info(info)
```

### URL Patterns (Full Coverage)

```python
YOUTUBE_PLAYLIST_PATTERNS = [
    # Стандартный формат плейлиста
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"),
    # Embed формат для плейлистов
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/videoseries\?list=([a-zA-Z0-9_-]+)"),
    # Параметр list в любом URL (watch, и т.д.)
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/[^?]*[?&]list=([a-zA-Z0-9_-]+)"),
]
```

**Покрываемые форматы URL:**
- `youtube.com/playlist?list=xxx`
- `www.youtube.com/playlist?list=xxx`
- `m.youtube.com/playlist?list=xxx` (мобильная версия)
- `youtube.com/embed/videoseries?list=xxx` (embed)
- `youtube.com/watch?v=yyy&list=xxx` (видео в контексте плейлиста)
- `youtube.com/watch?list=xxx&v=yyy` (порядок параметров не важен)

### Config Options

| Option      | Default | Description |
|-------------|---------|-------------|
| `lang`      | `"ru"` | Язык метаданных (en, ru, de, etc.) |
| `with_list` | `True` | Включать ли список видео в вывод |

### Extracted Fields

**Playlist metadata:**
- id: playlist ID
- url: canonical playlist URL
- title: playlist title
- description: playlist description
- channel: channel name
- channel_url: channel URL
- video_count: number of videos
- videos: list of video entries (id, title, url, duration) — только если with_list=True

### Output Format (Markdown)

```markdown
# Playlist Title

**URL:** https://www.youtube.com/playlist?list=xxx
**Channel:** [Channel Name](channel_url)
**Videos:** 42

## Description

Playlist description...

## Videos

1. [Video Title 1](https://www.youtube.com/watch?v=xxx) - 10:30
2. [Video Title 2](https://www.youtube.com/watch?v=yyy) - 5:45
...
```

## Next Steps

После завершения задач:
1. `uv tool install .` для переустановки CLI
2. Тестирование: `conget-youtube-playlist "https://www.youtube.com/playlist?list=xxx"`
3. Тестирование через main CLI: `conget fetch "https://www.youtube.com/playlist?list=xxx"`
