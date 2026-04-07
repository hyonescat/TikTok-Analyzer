# TikTok Favorites & Liked Videos Analyzer — Design Spec

**Date:** 2026-04-06
**Status:** Approved — ready for implementation

## Additional Requirements
- Project lives in its own folder: `~/Documents/tiktok-analyzer/`
- Git commits made at each logical milestone during implementation
- GitHub repo to be created: `TikTok-Analyzer` (via GitHub API)
- `.gitignore` must exclude: `cookies/`, `transcripts/`, `extractions/`, `output/`, `logs/`

---

## Context

The user regularly saves and likes developer-focused TikTok videos. Over time these accumulate into an untapped resource: a personalized signal of what tools, extensions, AI models, CLIs, and workflows are worth exploring. This tool automates the extraction of that signal — scraping favorited and liked videos, transcribing them locally, running structured LLM extraction, and producing a ranked developer setup to-do list. A local web UI makes results browsable, filterable, and actionable. All processing runs inside Docker on Apple Silicon (M3), using the host machine's existing Ollama installation rather than spinning up a duplicate LLM service inside Docker.

---

## Project Location

Standalone project — completely separate from World Monitor.

```
~/Documents/tiktok-analyzer/
```

No shared code, dependencies, or deployment with World Monitor.

---

## Architecture

### Containers (docker-compose.yml)

Two containers only, `linux/arm64` platform:

```
┌─────────────────────────────────────────────────┐
│  Docker Desktop (linux/arm64)                   │
│                                                 │
│  ┌──────────────────┐    ┌──────────────────┐  │
│  │   analyzer       │◄───│      ui          │  │
│  │  Python + FastAPI│    │  nginx + Vue 3   │  │
│  │  :8000 (internal)│    │  :8080 (host)    │  │
│  └────────┬─────────┘    └──────────────────┘  │
│           │                                     │
└───────────┼─────────────────────────────────────┘
            │ http://host.docker.internal:11434
            ▼
  ┌─────────────────────┐
  │  Host Mac (M3)      │
  │  Ollama (native)    │
  │  Any local LLM      │
  └─────────────────────┘
```

**`analyzer` container:**
- Base image: `mcr.microsoft.com/playwright/python:v1.44.0-jammy`
- Platform: `linux/arm64`
- Runs FastAPI server on port 8000 (internal only)
- Spawns `analyze.py` as subprocesses on demand
- Handles all scraping, transcription, LLM extraction, ranking

**`ui` container:**
- Base image: nginx (alpine)
- Platform: `linux/arm64`
- Serves compiled Vue 3 SPA on port 8080 (exposed to host)
- Proxies `/api/*` → `analyzer:8000`

**No `ollama` container.** The host machine's Ollama is used via `host.docker.internal:11434`. Configurable via `OLLAMA_HOST` env var.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Host Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | LLM model to use |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `WHISPER_DEVICE` | `cpu` | CPU-only for M3 |
| `WHISPER_COMPUTE_TYPE` | `int8` | M3 compatible |
| `MAX_RETRIES` | `3` | Retry limit for scraping/LLM |
| `RATE_LIMIT_DELAY` | `2.5` | Seconds between TikTok requests |

---

## Project Structure

```
tiktok-analyzer/
├── docker-compose.yml
├── Dockerfile                    # analyzer image
├── requirements.txt
├── analyze.py                    # CLI entrypoint (runs standalone or via API)
├── api/
│   └── server.py                 # FastAPI app
├── core/
│   ├── collector.py              # Playwright scraper (favorites + liked)
│   ├── transcriber.py            # yt-dlp + faster-whisper
│   ├── extractor.py              # General tool extraction via Ollama
│   ├── analyzer.py               # Structured per-video extraction (technologies, extensions, modules, AI)
│   ├── ranker.py                 # Scoring + aggregation across all videos
│   └── history.py                # history.json read/write + dedup logic
├── ui/
│   ├── Dockerfile                # nginx + pre-built Vue assets
│   ├── nginx.conf                # proxy /api/* → analyzer:8000
│   └── src/
│       ├── App.vue               # Tab navigation + run status bar
│       ├── views/
│       │   ├── Progress.vue      # Live SSE feed: logs + transcripts + analysis cards
│       │   ├── Results.vue       # Filterable/searchable ranked tool table
│       │   ├── TodoList.vue      # Rendered todo_list.md with checkboxes
│       │   └── History.vue       # All previously analyzed videos
│       └── components/
│           ├── RunModal.vue      # Run config (counts, flags) + launch button
│           ├── TranscriptCard.vue # Collapsible transcript per video
│           └── VideoAnalysisCard.vue # Structured extraction per video
├── cookies/                      # gitignored — TikTok session cookies
├── transcripts/                  # gitignored — per-video .txt and .json
├── extractions/                  # gitignored — per-video LLM extraction JSON
├── output/                       # gitignored — final outputs + history + progress
└── logs/                         # gitignored — error logs, run summaries
```

---

## Core Features

### 1. TikTok Video Collector (`core/collector.py`)

- Playwright (Chromium, headless) authenticated via `./cookies/cookies.txt` (Netscape format)
- Collects from two sources: **Favorites tab** and **Liked Videos tab**
- Deduplicates by `video_id` across both sources; tags each with `source: favorites | liked | both`
- Checks `history.json` before collecting — skips any `video_id` already analyzed
- Per-video fields extracted: `video_id`, `url`, `caption`, `hashtags`, `source`, `author_username`, `author_display_name`, `like_count`, `comment_count`, `share_count`, `play_count`, `video_duration`, `posted_date`
- Anti-detection: randomized scroll speed, 2–5s delays between actions
- Rate limit handling: on HTTP 429 → wait 30s, retry up to `MAX_RETRIES`
- Progress saved to `./output/progress.json` on interruption; resumed on next run
- Cookie validation on startup: warns on expiry, exits with re-export instructions if auth fails

### 2. Transcription (`core/transcriber.py`)

- `yt-dlp` extracts audio (`-x --audio-format mp3`) using cookies file
- `faster-whisper` transcribes with `device=cpu`, `compute_type=int8`
- **Cache-first:** if `./transcripts/<video_id>.txt` exists, skip download and transcription
- Saves per video:
  - `./transcripts/<video_id>.txt` — plain transcript text
  - `./transcripts/<video_id>.json` — metadata (url, caption, hashtags, source, author_username, author_display_name, like_count, comment_count, share_count, play_count, posted_date, transcription_date, model, duration, word_count)
- On yt-dlp failure (deleted/geo-blocked/private): logs to `./logs/failed_videos.json`, skips, continues

### 3. General Tool Extraction (`core/extractor.py`)

Combines caption + hashtags + transcript → sends to Ollama. Model responds only in valid JSON, no preamble.

**Extraction schema per item:**
```json
{
  "tool": "exact tool name",
  "category": "extension|repo|service|cli|framework|ai_model|workflow|hardware",
  "description": "one sentence description",
  "install_command": "brew install X or npm install X if known, else null",
  "url": "official URL if known, else null"
}
```

- Invalid JSON: retry up to 3× with stricter prompt. After 3 failures: save to `./logs/llm_failures.json`, skip video, continue.
- Saved to `./extractions/<video_id>.json`

### 4. Structured Analysis (`core/analyzer.py`)

Dedicated extraction component that runs **in addition to** general extraction. Produces a normalized, category-specific breakdown per video:

```json
{
  "video_id": "...",
  "technologies": ["Docker", "Kubernetes", "Nix"],
  "extensions": ["Continue", "GitLens", "Cursor"],
  "modules": ["httpx", "pydantic", "faster-whisper"],
  "ai_components": ["RAG pipeline", "embeddings", "function calling"],
  "ai_names": ["Claude", "Ollama", "Qwen2.5", "Whisper"]
}
```

Saved to `./extractions/<video_id>_analysis.json`. Results are merged into the ranker's input and surfaced in the UI's `VideoAnalysisCard`.

### 5. History Registry (`core/history.py`)

- Persistent record in `./output/history.json` keyed by `video_id`
- Written after each successful extraction
- Fields: `video_id`, `url`, `caption`, `source`, `author_username`, `author_display_name`, `like_count`, `comment_count`, `share_count`, `play_count`, `posted_date`, `analyzed_date`, `tool_count`, `run_id`
- Used by collector to skip already-processed videos on all future runs
- Supports `--reprocess <video_id>` flag to force re-run a specific video

### 6. Ranking Engine (`core/ranker.py`)

Aggregates all extractions across all videos:

| Signal | Weight |
|--------|--------|
| Mention count | Base score = N |
| Found in both favorites AND liked | × 1.5 |
| Category: `ai_model`, `cli`, `extension` | × 1.3 |
| Category: `workflow`, `hardware` | × 0.8 |

Sorted descending by final score, grouped by category. Each tool entry in `tools_ranked.json` includes a `sources` array — list of `{ video_id, author_username, source }` records for every video that mentioned it, enabling author and source filtering in the UI. Output:
- `./output/tools_ranked.json` — full scored list with per-tool source attribution
- `./output/todo_list.md` — human-readable ranked to-do list

### 7. Output Files

| File | Description |
|------|-------------|
| `./output/todo_list.md` | Human-readable ranked to-do list |
| `./output/tools_ranked.json` | Full aggregated JSON with scores |
| `./output/history.json` | All analyzed video records |
| `./output/progress.json` | Checkpoint for resuming interrupted runs |
| `./logs/failed_videos.json` | Videos that failed to download/transcribe |
| `./logs/llm_failures.json` | Videos where LLM extraction failed |
| `./logs/run_summary.txt` | Stats: videos processed, tools found, run time, errors |

---

## API (`api/server.py`)

FastAPI app running on port 8000. Only one analysis run at a time.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Start analysis. Params: `favorites`, `liked`, `favorites_only`, `dry_run`, `reprocess` (video_id) |
| `GET` | `/api/progress` | SSE stream of live run output |
| `GET` | `/api/status` | Current state: `idle \| running \| done \| error` |
| `GET` | `/api/results` | Returns `tools_ranked.json` |
| `GET` | `/api/results/todo` | Returns `todo_list.md` as text |
| `POST` | `/api/run/cancel` | Kill the running subprocess |

**SSE event types on `/api/progress`:**

```json
{ "event": "log", "data": "Collected 47 favorites" }
{ "event": "transcript", "data": { "video_id": "...", "caption": "...", "source": "favorites", "author_username": "...", "like_count": 42300, "text": "..." } }
{ "event": "analysis", "data": { "video_id": "...", "technologies": [...], "extensions": [...], "modules": [...], "ai_components": [...], "ai_names": [...] } }
{ "event": "done", "data": { "videos": 97, "tools": 43, "duration_seconds": 412 } }
{ "event": "error", "data": "..." }
```

- `POST /api/run` while run is active → `409 Conflict`
- `POST /api/run/cancel` → kills subprocess, emits `{ "event": "error", "data": "Cancelled by user" }`

---

## Vue 3 UI

Single-page app, 4 tabs, served by nginx on port 8080.

### Global header
- App title
- Status badge: `idle` / `running` / `done` / `error`
- **Run button** → opens `RunModal.vue` (config: favorites count, liked count, favorites-only toggle, dry-run toggle)
- While running: button becomes **Cancel**

### Progress tab (`Progress.vue`)
Live SSE feed. Shows:
- Log lines as they stream in
- `TranscriptCard.vue` per video (collapsible transcript + metadata)
- `VideoAnalysisCard.vue` per video (structured table: technologies, extensions, modules, AI components, AI names)

### Results tab (`Results.vue`)
- Filter by category dropdown (extension, cli, ai_model, framework, repo, service, workflow, hardware)
- Filter by source (favorites / liked / both)
- Filter by author (dropdown populated from history)
- Text search across tool names and descriptions
- Sorted by score descending
- Each row: tool name, category badge, score, install command, URL, sourced-from authors

### To-Do List tab (`TodoList.vue`)
- Rendered markdown of `todo_list.md`
- Interactive checkboxes
- Copy-to-clipboard button

### History tab (`History.vue`)
- All previously analyzed videos from `history.json`
- Filter by source (favorites / liked / both)
- Filter by author (dropdown populated from all known authors)
- Filter by extracted category (shows only videos that mentioned tools in that category)
- Text search by caption or author
- Per-video summary: author, like/comment/share/play counts, posted date, tool count
- Per-video: shows `VideoAnalysisCard` on expand
- Force-reprocess button per video (sends `POST /api/run` with `reprocess=<video_id>`)

---

## Cookie Export Guide

1. Install **Get cookies.txt LOCALLY** Chrome extension
2. Log into TikTok in Chrome
3. Navigate to `https://www.tiktok.com`
4. Click extension → Export → save as `cookies.txt`
5. Place in `./cookies/cookies.txt`

The analyzer validates cookies on startup and exits with clear instructions if expired.

---

## CLI Usage

```bash
# First-time setup
docker compose build
mkdir -p transcripts extractions output logs cookies

# Full analysis (favorites + liked, 50 each)
docker compose run analyzer python analyze.py --favorites 50 --liked 50

# Favorites only
docker compose run analyzer python analyze.py --favorites-only --favorites 20

# Rebuild output from cache (no scraping or transcription)
docker compose run analyzer python analyze.py --rebuild-output

# Force reprocess a specific video
docker compose run analyzer python analyze.py --reprocess <video_id>

# Dry run — collect video list only
docker compose run analyzer python analyze.py --dry-run --favorites 10

# Start the full stack (UI + analyzer API)
docker compose up
# → UI available at http://localhost:8080
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Cookie file missing | Exit with setup instructions |
| Cookie expired / auth failed | Exit with re-export instructions |
| TikTok rate-limits scraper | Wait 30s, retry up to 3×, save progress, exit gracefully |
| yt-dlp fails on a video | Log to `failed_videos.json`, skip, continue |
| LLM returns invalid JSON | Retry 3×, log to `llm_failures.json`, skip |
| Ollama not reachable | Exit with clear message pointing to host Ollama |
| Run interrupted mid-way | Resume from `progress.json` on next run |
| `/api/run` called during active run | Return `409 Conflict` |

---

## Verification

```bash
# 1. Build images
docker compose build

# 2. Dry run — verify scraping and cookie auth work
docker compose run analyzer python analyze.py --favorites 5 --dry-run

# 3. Single video transcription test
docker compose run analyzer python analyze.py --reprocess <known_video_id>

# 4. Full stack UI test
docker compose up
# Open http://localhost:8080
# Click Run → set favorites=5, liked=5 → verify:
#   - Progress tab shows live log lines
#   - TranscriptCard appears per video
#   - VideoAnalysisCard appears with structured extraction
#   - Results tab populates after run
#   - History tab shows analyzed videos
#   - To-Do List tab shows ranked markdown

# 5. Resume test — interrupt a run mid-way (Ctrl+C), restart, verify it resumes from checkpoint
```
