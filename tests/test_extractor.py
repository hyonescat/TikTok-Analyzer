import json
import pytest
from unittest.mock import patch, MagicMock
from core.extractor import extract_tools, _call_ollama
from core.models import VideoRecord, ExtractedTool


def make_video(video_id="v1"):
    return VideoRecord(
        video_id=video_id, url="https://tiktok.com/@u/video/v1",
        caption="How I use Docker daily", hashtags=["docker", "devops"],
        source="favorites", author_username="devuser",
        author_display_name="Dev", like_count=100,
        comment_count=5, share_count=2, play_count=500,
    )


MOCK_RESPONSE = json.dumps([
    {"tool": "Docker", "category": "cli", "description": "Container runtime",
     "install_command": "brew install docker", "url": "https://docker.com"}
])


def test_extract_tools_calls_ollama(tmp_dir):
    with patch("core.extractor._call_ollama", return_value=MOCK_RESPONSE):
        tools = extract_tools(make_video(), "I use Docker every day", tmp_dir)
    assert len(tools) == 1
    assert tools[0].tool == "Docker"
    assert tools[0].category == "cli"


def test_extract_tools_uses_cache(tmp_dir):
    cache = tmp_dir / "v1.json"
    cache.write_text(MOCK_RESPONSE)
    with patch("core.extractor._call_ollama") as mock_llm:
        tools = extract_tools(make_video(), "transcript", tmp_dir)
    mock_llm.assert_not_called()
    assert tools[0].tool == "Docker"


def test_extract_tools_retries_on_invalid_json(tmp_dir):
    responses = ["not json", "also not json", MOCK_RESPONSE]
    with patch("core.extractor._call_ollama", side_effect=responses):
        tools = extract_tools(make_video(), "transcript", tmp_dir)
    assert tools[0].tool == "Docker"


def test_extract_tools_raises_after_three_failures(tmp_dir):
    with patch("core.extractor._call_ollama", return_value="bad json"):
        with pytest.raises(Exception):
            extract_tools(make_video(), "transcript", tmp_dir)


def test_extract_tools_strips_markdown_fences(tmp_dir):
    fenced = f"```json\n{MOCK_RESPONSE}\n```"
    with patch("core.extractor._call_ollama", return_value=fenced):
        tools = extract_tools(make_video(), "transcript", tmp_dir)
    assert tools[0].tool == "Docker"
