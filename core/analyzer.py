from __future__ import annotations
import json
import os
from pathlib import Path
import httpx
from .models import VideoAnalysis, VideoRecord

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

_PROMPT = """Analyze this TikTok video and extract ONLY items explicitly mentioned.

Respond ONLY with a JSON object matching this exact schema:
{{"technologies": ["..."], "extensions": ["..."], "modules": ["..."], "ai_components": ["..."], "ai_names": ["..."]}}

- technologies: general tech (Docker, Kubernetes, Linux, macOS, etc.)
- extensions: editor extensions/plugins (VS Code, Cursor, JetBrains extensions)
- modules: npm/pip/brew installable packages and libraries
- ai_components: AI techniques/patterns (RAG, embeddings, function calling, fine-tuning)
- ai_names: specific AI models/products (Claude, GPT-4, Ollama, Whisper, Qwen, Gemini)

Return empty arrays for categories with no mentions. No explanation, no markdown.

VIDEO CONTENT:
Caption: {caption}
Hashtags: {hashtags}
Transcript: {transcript}"""


def _call_ollama(prompt: str) -> str:
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"]


def analyze_video(video: VideoRecord, transcript: str, extractions_dir: Path) -> VideoAnalysis:
    cache_file = extractions_dir / f"{video.video_id}_analysis.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return VideoAnalysis(**data)

    hashtags_str = " ".join(video.hashtags)
    prompt = _PROMPT.format(
        caption=video.caption, hashtags=hashtags_str, transcript=transcript
    )

    raw = _call_ollama(prompt).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    for key in ("technologies", "extensions", "modules", "ai_components", "ai_names"):
        data.setdefault(key, [])

    analysis = VideoAnalysis(video_id=video.video_id, **data)
    extractions_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(analysis.model_dump(), indent=2))
    return analysis
