# Plan: Add with_subs option to YouTube video fetcher

## Overview
Add a `with_subs` configuration option to `YoutubeVideoFetcher` that controls whether subtitles/transcript are included in fetch result.

**Branch:** `feature/yt-video-with-subs`
**Created:** 2026-02-22

## Settings
- **Testing:** No
- **Logging:** Minimal (WARN/ERROR only)
- **Docs:** Yes (run /aif-docs after implementation)

## Implementation Notes

### yt-dlp Subtitle Structure

Based on `yt_dlp/extractor/common.py` documentation:

**Subtitles in info_dict:**
- `info_dict['subtitles']` - Dictionary of manual subtitles by language code (key: lang_code, value: list of subtitle formats)
- `info_dict['automatic_captions']` - Dictionary of auto-generated captions by language code

**Subtitle entry structure:**
Each entry in `subtitles[lang]` is a sorted list where each element has:
- `"ext"` - File extension (usually 'vtt')
- Either `"data"` or `"url"`:
  - `"data"`: The subtitles file contents (as plain string, NOT base64 encoded)
  - `"url"`: URL pointing to subtitles file (alternative to data)

**Required ydl_opts for subtitle extraction:**
- `"writesubtitles": True` - Enable subtitle extraction
- `"subtitleslangs": ["lang"]` - Specify which languages to extract

The language for subtitle extraction should match the `lang` config option of the fetcher.

## Tasks

### Phase 1: Configuration

1. ~~**Add with_subs config option to metadata~~
   - File: `src/fetchers/youtube_video.py`
   - Add boolean option with default `False` to `metadata.config_options`
   - Description: "Include subtitles/transcript in output"

### Phase 2: Subtitle Extraction

2. ~~**Implement subtitle extraction from yt-dlp**~~
   - File: `src/fetchers/youtube_video.py`
   - ~~Add `writesubtitles` and `subtitleslangs` to `ydl_opts` when `with_subs=True`~~
   - ~~Use priority language from `lang` config option for `subtitleslangs`~~
   - ~~Extract subtitle data from `info_dict['subtitles']` and `info_dict['automatic_captions']`~~
   - ~~Try manual subtitles first, then auto captions in the priority language~~
   - ~~Get subtitle content from the `"data"` field (plain text, not base64)~~
   - ~~Handle missing subtitles gracefully~~

3. ~~**Add subtitles field to extracted video data**~~
   - ~~File: `src/fetchers/youtube_video.py`~~
   - ~~Update `_extract_fields()` to include subtitles in return dict~~
   - ~~Structure: `{"lang": "ru", "text": "..."}`~~
   - ~~Set to `None` if no subtitles found~~
   - ~~Update `_extract_fields()` to include subtitles in return dict~~
   - ~~Structure: `{"lang": "ru", "text": "..."}`~~
   - ~~Set to `None` if no subtitles found~~

### Phase 3: Output Formatting

4. ~~**Format subtitles in output**~~
   - File: `src/fetchers/youtube_video.py`
   - Update `_format_output()` to add "## Subtitles" section in markdown
   - Include in JSON output via data dict
   - Display language code and subtitle text content

## Commit Plan

Since this plan has 4 tasks (< 5), a single commit will be made at the end.
