# TikTok Analyzer

Analyze your TikTok favorites and liked videos locally. Extracts technologies, tools, extensions, and AI models mentioned in videos and produces a ranked developer setup to-do list.

## Requirements
- Docker Desktop for Mac (Apple Silicon)
- Ollama running locally with a model pulled (default: `qwen2.5:7b`)
- TikTok browser cookies exported to `./cookies/cookies.txt`

## Quick Start
```bash
cp .env.example .env       # configure environment
docker compose build
docker compose up          # UI at http://localhost:8080
```

## Cookie Export
1. Install "Get cookies.txt LOCALLY" Chrome extension
2. Log into TikTok at https://www.tiktok.com
3. Click extension → Export → save as `cookies/cookies.txt`
