# Plan: YouTube Video Fetcher

**Branch:** feature/youtube-video-fetcher
**Created:** 2026-02-21

## Settings

- **Testing:** No
- **Logging:** Minimal (WARN/ERROR only)
- **Docs:** Yes (update DESCRIPTION.md)

## Description

Добавить новый фетчер `youtube-video` для извлечения метаданных YouTube видеороликов с использованием yt-dlp (без аутентификации, без скачивания видео).

## Tasks

### Phase 1: Dependencies

- [x] **Task #1**: Добавить yt-dlp в зависимости pyproject.toml
  - Файл: `pyproject.toml`
  - Добавить `yt-dlp` в dependencies

### Phase 2: Implementation

- [x] **Task #2**: Создать YoutubeVideoFetcher в src/fetchers/youtube_video.py
  - Файл: `src/fetchers/youtube_video.py`
  - Зависит от: Task #1
  - Класс YoutubeVideoFetcher наследует BaseFetcher
  - URL patterns: youtube.com/watch, youtu.be/, youtube.com/embed, youtube.com/v
  - Config option: `lang` (default="en") — язык метаданных
  - Извлекаемые поля: id, title, description, duration, duration_string, view_count, like_count, comment_count, upload_date, uploader, channel, channel_url, channel_id, thumbnail, tags
  - Форматы: markdown, text, json
  - yt-dlp options: quiet=True, no_warnings=True, extractor_args={'youtube': {'lang': [lang]}}
  - Обработка ошибок: yt_dlp.DownloadError/ExtractorError → FetchError
  - Для text-формата использовать src.core.formatters.markdown_to_text()

### Phase 3: Registration

- [x] **Task #3**: Зарегистрировать youtube-video в entry-points pyproject.toml
  - Файл: `pyproject.toml`
  - CLI script: conget-youtube-video
  - Entry-point: youtube-video

### Phase 4: Documentation

- [x] **Task #4**: Обновить DESCRIPTION.md с новым фетчером
  - Файл: `.ai-factory/DESCRIPTION.md`
  - Зависит от: Task #2
  - Добавить описание YoutubeVideoFetcher

## Implementation Notes

### yt-dlp Usage Pattern

```python
from yt_dlp import YoutubeDL

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'lang': [lang],  # e.g., 'ru', 'en', 'de'
        },
    },
}
with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    info_dict = ydl.sanitize_info(info)
```

### URL Patterns (full coverage)

```python
YOUTUBE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})"),
]
```

### URL Normalization

Исходный URL может содержать дополнительные параметры (playlist, t, index и т.д.).
Нормализация:
1. Извлечь video_id (11 символов) из URL
2. Построить канонический URL: `https://www.youtube.com/watch?v={video_id}`
3. Передать канонический URL в yt-dlp

## Next Steps

После завершения задач:
1. `uv tool install .` для переустановки CLI
2. Тестирование: `conget-youtube-video "https://www.youtube.com/watch?v=xxx"`
3. Тестирование через main CLI: `conget fetch "https://www.youtube.com/watch?v=xxx"`
