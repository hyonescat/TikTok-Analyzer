import pytest
from core.models import (
    VideoRecord, ExtractedTool, VideoAnalysis,
    HistoryRecord, RankedTool, ToolSource, RunConfig
)

def test_video_record_requires_fields():
    v = VideoRecord(
        video_id="abc123", url="https://tiktok.com/@user/video/abc123",
        caption="Test video", hashtags=["dev", "tools"], source="favorites",
        author_username="devuser", author_display_name="Dev User",
        like_count=1000, comment_count=50, share_count=20, play_count=5000,
    )
    assert v.video_id == "abc123"
    assert v.source == "favorites"
    assert v.video_duration is None

def test_video_record_invalid_source():
    with pytest.raises(Exception):
        VideoRecord(
            video_id="x", url="u", caption="c", hashtags=[],
            source="invalid",
            author_username="u", author_display_name="U",
            like_count=0, comment_count=0, share_count=0, play_count=0,
        )

def test_extracted_tool_optional_fields():
    t = ExtractedTool(tool="Docker", category="cli", description="Container runtime")
    assert t.install_command is None
    assert t.url is None

def test_extracted_tool_invalid_category():
    with pytest.raises(Exception):
        ExtractedTool(tool="X", category="unknown", description="Y")

def test_video_analysis_defaults():
    a = VideoAnalysis(video_id="abc123")
    assert a.technologies == []
    assert a.ai_names == []

def test_run_config_defaults():
    cfg = RunConfig()
    assert cfg.favorites == 50
    assert cfg.liked == 50
    assert cfg.dry_run is False
    assert cfg.reprocess is None
