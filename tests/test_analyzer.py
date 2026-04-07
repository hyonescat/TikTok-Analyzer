import json
import pytest
from unittest.mock import patch
from core.analyzer import analyze_video
from core.models import VideoRecord, VideoAnalysis


def make_video(video_id="v1"):
    return VideoRecord(
        video_id=video_id, url="https://tiktok.com/@u/video/v1",
        caption="My AI dev setup", hashtags=["ai", "dev"],
        source="liked", author_username="aidev",
        author_display_name="AI Dev", like_count=500,
        comment_count=10, share_count=5, play_count=2000,
    )


MOCK_ANALYSIS = {
    "technologies": ["Docker", "Linux"],
    "extensions": ["Continue", "GitLens"],
    "modules": ["httpx", "pydantic"],
    "ai_components": ["RAG pipeline", "embeddings"],
    "ai_names": ["Claude", "Ollama"],
}


def test_analyze_video_returns_video_analysis(tmp_dir):
    with patch("core.analyzer._call_ollama", return_value=json.dumps(MOCK_ANALYSIS)):
        result = analyze_video(make_video(), "I use Docker and Claude", tmp_dir)
    assert isinstance(result, VideoAnalysis)
    assert result.video_id == "v1"
    assert "Docker" in result.technologies
    assert "Claude" in result.ai_names


def test_analyze_video_uses_cache(tmp_dir):
    cached = {"video_id": "v1", **MOCK_ANALYSIS}
    (tmp_dir / "v1_analysis.json").write_text(json.dumps(cached))
    with patch("core.analyzer._call_ollama") as mock:
        result = analyze_video(make_video(), "transcript", tmp_dir)
    mock.assert_not_called()
    assert result.ai_names == ["Claude", "Ollama"]


def test_analyze_video_strips_fences(tmp_dir):
    fenced = f"```json\n{json.dumps(MOCK_ANALYSIS)}\n```"
    with patch("core.analyzer._call_ollama", return_value=fenced):
        result = analyze_video(make_video(), "transcript", tmp_dir)
    assert "Continue" in result.extensions


def test_analyze_video_empty_lists_on_missing_keys(tmp_dir):
    partial = {"technologies": ["Docker"]}
    with patch("core.analyzer._call_ollama", return_value=json.dumps(partial)):
        result = analyze_video(make_video(), "transcript", tmp_dir)
    assert result.extensions == []
    assert result.ai_names == []
