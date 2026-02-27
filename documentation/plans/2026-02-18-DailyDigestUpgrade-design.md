# Daily Digest Video Upgrade - Design Document

**Date:** 2026-02-18
**Status:** Approved for Implementation

## Overview

At midnight GMT, automatically compile the day's news stories into a single video, upload to YouTube, and add to a "Daily Summary" playlist. This provides an archived, shareable format for each day's verified facts.

---

## Design Decisions

| Aspect | Decision |
|--------|----------|
| **Trigger** | Midnight GMT, integrated with existing `check_midnight_archive()` |
| **Video tool** | FFmpeg (single pipeline command) |
| **Visuals** | Rotating seasonal backgrounds with crossfade (~50 sec per image) |
| **Text overlays** | Full fact text + source attribution, timed to each audio segment |
| **Pacing** | 2-3 second silence inserted between stories |
| **Intro/Outro** | None - pure facts, no framing |
| **YouTube auth** | OAuth 2.0 with guided first-time setup script |
| **Playlist** | Auto-add to "Daily Summary" playlist |
| **Local storage** | Always save to `video/YYYY-MM-DD-daily-summary.mp4` |
| **Video retention** | Keep forever locally |
| **Audio archiving** | Move to `audio/archive/YYYY-MM-DD/` before video generation |
| **Failure handling** | Retry 3x with exponential backoff, SMS alert on failure |

---

## Video Specifications

- **Resolution:** 1920x1080 (standard HD)
- **Codec:** H.264 (libx264) for broad compatibility
- **Audio:** AAC (converted from MP3 sources)
- **Frame rate:** 30fps
- **Format:** MP4

---

## Midnight Sequence (Revised)

```
Midnight GMT triggers check_midnight_archive():

1. archive_daily_log()                    # Existing - compress daily log

2. archive_audio_files(yesterday)         # NEW - move audio to safe location
   └── audio/audio_*.mp3 → audio/archive/YYYY-MM-DD/

3. generate_daily_video(yesterday)        # NEW - build video from archived audio
   └── Collect stories from yesterday's data
   └── Calculate audio durations with ffprobe
   └── Select seasonal background images
   └── Build FFmpeg command with:
       - Concatenated audio (with 2-3s silence gaps)
       - Crossfading image slideshow
       - Timed text overlays for each story
   └── Render to video/YYYY-MM-DD-daily-summary.mp4

4. upload_to_youtube(video_path)          # NEW - upload and playlist
   └── Authenticate (refresh tokens if needed)
   └── Upload with metadata:
       - Title: "JTF News Daily Summary - YYYY-MM-DD"
       - License: Creative Commons
       - Category: News & Politics
   └── Add to Daily Summary playlist

5. cleanup_old_data(days=7)               # Existing - clean cache files
   └── Does NOT touch audio/archive/ or video/
```

---

## New Functions

### `archive_audio_files(date: str) -> list[str]`
Move current day's audio files to archive folder before they get overwritten.

```python
def archive_audio_files(date: str) -> list[str]:
    """Archive audio files for the given date. Returns list of archived paths."""
    archive_dir = AUDIO_DIR / "archive" / date
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = []
    for audio_file in sorted(AUDIO_DIR.glob("audio_*.mp3")):
        dest = archive_dir / audio_file.name
        shutil.move(audio_file, dest)
        archived.append(str(dest))

    return archived
```

### `get_audio_duration(path: str) -> float`
Use ffprobe to get precise duration of an audio file.

```python
def get_audio_duration(path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())
```

### `generate_daily_video(date: str, stories: list, audio_files: list) -> str`
Build and execute FFmpeg command to generate the daily summary video.

**Inputs:**
- `date`: YYYY-MM-DD string
- `stories`: List of story dicts with `fact` and `source` fields
- `audio_files`: Ordered list of audio file paths

**Process:**
1. Calculate duration of each audio file
2. Generate 2-3 seconds of silence for gaps
3. Select background images from current season folder
4. Build FFmpeg filter_complex:
   - Audio: concat all audio files with silence gaps
   - Video: loop through images with crossfade transitions
   - Text: drawtext filter for each story, timed to audio segment
5. Execute FFmpeg, output to `video/YYYY-MM-DD-daily-summary.mp4`

### `upload_to_youtube(video_path: str, date: str) -> str`
Upload video to YouTube and add to playlist.

**Returns:** YouTube video ID on success

**Error handling:**
- Retry 3x with exponential backoff (30s, 60s, 120s)
- On all retries fail: send SMS alert, return None
- Video file preserved locally regardless of upload status

### `generate_and_upload_daily_summary(date: str)`
Orchestrator function called from `check_midnight_archive()`.

```python
def generate_and_upload_daily_summary(date: str):
    """Generate daily summary video and upload to YouTube."""

    # Load yesterday's stories
    stories = load_stories_for_date(date)
    if not stories:
        log.info(f"No stories for {date}, skipping video generation")
        return

    # Archive audio files (move to safe location)
    audio_files = archive_audio_files(date)
    if not audio_files:
        log.warning(f"No audio files found for {date}")
        return

    # Generate video
    try:
        video_path = generate_daily_video(date, stories, audio_files)
        log.info(f"Generated daily video: {video_path}")
    except Exception as e:
        log.error(f"Video generation failed: {e}")
        send_alert(f"Daily video generation failed for {date}: {e}")
        return

    # Upload to YouTube
    video_id = upload_to_youtube(video_path, date)
    if video_id:
        log.info(f"Uploaded to YouTube: {video_id}")
    else:
        log.error(f"YouTube upload failed for {date}, video saved locally")
```

---

## New Files & Folders

| Path | Purpose |
|------|---------|
| `video/` | Daily summary videos (kept forever) |
| `audio/archive/YYYY-MM-DD/` | Archived audio files per day (kept forever) |
| `client_secrets.json` | OAuth credentials (downloaded once from Google Cloud) |
| `data/youtube_tokens.json` | OAuth refresh tokens (auto-managed) |

---

## New Dependencies

```
google-api-python-client    # YouTube Data API v3
google-auth-oauthlib        # OAuth 2.0 authentication
```

**System requirement:** FFmpeg must be installed on both dev and deploy machines.

---

## New .env Keys

```
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
YOUTUBE_PLAYLIST_ID=PLxxxxxx
```

---

## First-Time Setup Script

A guided setup script (`setup_youtube.py`) will walk through:

1. **Google Cloud Console setup**
   - Create new project (or use existing)
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download client_secrets.json

2. **Initial authentication**
   - Open browser for Google sign-in
   - Grant YouTube upload permissions
   - Save refresh token to data/youtube_tokens.json

3. **Playlist setup**
   - Create "Daily Summary" playlist if it doesn't exist
   - Save playlist ID to .env

The script will pause at each step with clear instructions.

---

## Error Handling & Resilience

### Video Generation Failure
- Retry FFmpeg once on failure
- If still fails: log error, send SMS alert, skip upload
- Audio files preserved in archive folder for manual retry

### YouTube Upload Failure
- Retry 3x with exponential backoff (30s, 60s, 120s)
- If all fail: send SMS alert
- Video file preserved locally at `video/YYYY-MM-DD-daily-summary.mp4`
- Log includes local path for manual upload

### Playlist Addition Failure
- Non-critical (video already uploaded)
- Log warning, retry once
- If fails: log for manual playlist addition

### Edge Cases
- **No stories today:** Skip video generation, log info message
- **Missing audio files:** Generate with available files, log warning
- **YouTube service degraded:** Add to `_degraded_services`, video saved locally

---

## Deployment Notes

- Develop and debug on Apple Silicon dev machine
- Deploy to Intel/Mojave production machine via `deploy.sh`
- `video/` folder excluded from deploy (videos generated on deploy machine)
- `audio/archive/` also generated on deploy machine
- FFmpeg must be installed on deploy machine (`brew install ffmpeg`)

---

## Testing Plan

1. **Unit tests:**
   - `get_audio_duration()` with sample MP3
   - `archive_audio_files()` moves files correctly
   - FFmpeg command generation produces valid syntax

2. **Integration tests:**
   - Generate test video from sample stories/audio
   - Verify video plays correctly
   - Test YouTube upload to unlisted video

3. **End-to-end test:**
   - Manually trigger midnight sequence
   - Verify full flow: archive → generate → upload → playlist

---

## Future Considerations (Not in Scope)

- Thumbnail generation (auto-generate from first frame or custom template)
- Chapter markers in video description (timestamps per story)
- Automatic description with story list
- Multi-language summaries
