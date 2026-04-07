from __future__ import annotations
import json
import os
from pathlib import Path
import httpx
from .models import ExtractedTool, VideoRecord

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

_BASE_PROMPT = """You are a developer tool extraction engine. Given the following TikTok video content, extract every technology, tool, service, GitHub repo, VS Code extension, CLI tool, AI model, framework, or developer workflow mentioned.

Respond ONLY with a valid JSON array. No explanation, no markdown, no preamble.

Each item must follow this exact schema:
{{"tool": "exact tool name", "category": "extension|repo|service|cli|framework|ai_model|workflow|hardware", "description": "one sentence description", "install_command": "brew install X or npm install X if known, else null", "url": "official URL if known, else null"}}

VIDEO CONTENT:
Caption: {caption}
Hashtags: {hashtags}
Transcript: {transcript}"""

_STRICT_PROMPT = _BASE_PROMPT + "\n\nReturn ONLY a raw JSON array starting with [ and ending with ]. Absolutely no other text."


def _call_ollama(prompt: str) -> str:
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"]


def _parse_json(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


def extract_tools(video: VideoRecord, transcript: str, extractions_dir: Path) -> list[ExtractedTool]:
    cache_file = extractions_dir / f"{video.video_id}.json"
    if cache_file.exists():
        return [ExtractedTool(**t) for t in json.loads(cache_file.read_text())]

    hashtags_str = " ".join(video.hashtags)
    prompts = [
        _BASE_PROMPT.format(caption=video.caption, hashtags=hashtags_str, transcript=transcript),
        _STRICT_PROMPT.format(caption=video.caption, hashtags=hashtags_str, transcript=transcript),
        _STRICT_PROMPT.format(caption=video.caption, hashtags=hashtags_str, transcript=transcript),
    ]

    last_exc: Exception = RuntimeError("All attempts failed")
    for prompt in prompts:
        try:
            raw = _call_ollama(prompt)
            tools = [ExtractedTool(**t) for t in _parse_json(raw)]
            extractions_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps([t.model_dump() for t in tools], indent=2))
            return tools
        except Exception as e:
            last_exc = e

    raise last_exc
