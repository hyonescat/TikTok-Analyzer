import json
import pytest
from core.ranker import compute_score, aggregate
from core.models import VideoRecord, RankedTool


def make_video(video_id, source):
    return VideoRecord(
        video_id=video_id, url=f"https://tiktok.com/@u/video/{video_id}",
        caption="Test", hashtags=[], source=source,
        author_username="user", author_display_name="User",
        like_count=0, comment_count=0, share_count=0, play_count=0,
    )


def write_extraction(tmp_dir, video_id, tools):
    (tmp_dir / "extractions").mkdir(exist_ok=True)
    f = tmp_dir / "extractions" / f"{video_id}.json"
    f.write_text(json.dumps(tools))


def test_compute_score_base():
    assert compute_score(3, False, "service") == 3.0


def test_compute_score_both_multiplier():
    assert compute_score(2, True, "service") == 3.0


def test_compute_score_ai_model_multiplier():
    assert compute_score(2, False, "ai_model") == 2.6


def test_compute_score_workflow_multiplier():
    assert compute_score(10, False, "workflow") == 8.0


def test_aggregate_single_video(tmp_dir):
    videos = [make_video("v1", "favorites")]
    write_extraction(tmp_dir, "v1", [
        {"tool": "Docker", "category": "cli", "description": "Containers", "install_command": "brew install docker", "url": None}
    ])
    results = aggregate(tmp_dir / "extractions", videos)
    assert len(results) == 1
    assert results[0].tool == "Docker"
    assert results[0].mention_count == 1


def test_aggregate_both_sources_multiplier(tmp_dir):
    videos = [make_video("v1", "favorites"), make_video("v2", "liked")]
    write_extraction(tmp_dir, "v1", [
        {"tool": "Ollama", "category": "ai_model", "description": "Local LLMs", "install_command": None, "url": None}
    ])
    write_extraction(tmp_dir, "v2", [
        {"tool": "Ollama", "category": "ai_model", "description": "Local LLMs", "install_command": None, "url": None}
    ])
    results = aggregate(tmp_dir / "extractions", videos)
    assert len(results) == 1
    # mention_count=2, both=True (×1.5), ai_model (×1.3) → 2 × 1.5 × 1.3 = 3.9
    assert results[0].score == 3.9


def test_aggregate_sorted_by_score(tmp_dir):
    videos = [make_video("v1", "favorites"), make_video("v2", "favorites"), make_video("v3", "favorites")]
    write_extraction(tmp_dir, "v1", [{"tool": "A", "category": "service", "description": "d", "install_command": None, "url": None}])
    write_extraction(tmp_dir, "v2", [
        {"tool": "A", "category": "service", "description": "d", "install_command": None, "url": None},
        {"tool": "B", "category": "service", "description": "d2", "install_command": None, "url": None},
    ])
    write_extraction(tmp_dir, "v3", [{"tool": "A", "category": "service", "description": "d", "install_command": None, "url": None}])
    results = aggregate(tmp_dir / "extractions", videos)
    assert results[0].tool == "A"
    assert results[0].mention_count == 3
