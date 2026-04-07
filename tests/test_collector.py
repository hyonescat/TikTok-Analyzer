import pytest
from pathlib import Path
from core.collector import (
    load_cookies_file, validate_cookies_file,
    deduplicate_videos, merge_sources,
)
from core.models import VideoRecord


def make_video(video_id, source):
    return VideoRecord(
        video_id=video_id, url=f"https://t.com/@u/video/{video_id}",
        caption="Cap", hashtags=[], source=source,
        author_username="u", author_display_name="U",
        like_count=0, comment_count=0, share_count=0, play_count=0,
    )


def test_validate_cookies_file_missing(tmp_dir):
    with pytest.raises(FileNotFoundError):
        validate_cookies_file(tmp_dir / "cookies.txt")


def test_validate_cookies_file_exists(tmp_dir):
    f = tmp_dir / "cookies.txt"
    f.write_text("# Netscape HTTP Cookie File\ntiktok.com\tFALSE\t/\tFALSE\t0\tname\tvalue")
    validate_cookies_file(f)  # should not raise


def test_deduplicate_videos_removes_duplicates():
    videos = [make_video("v1", "favorites"), make_video("v1", "favorites"), make_video("v2", "liked")]
    result = deduplicate_videos(videos)
    assert len(result) == 2


def test_merge_sources_tags_both():
    favorites = [make_video("v1", "favorites"), make_video("v2", "favorites")]
    liked = [make_video("v1", "liked"), make_video("v3", "liked")]
    result = merge_sources(favorites, liked)
    by_id = {v.video_id: v for v in result}
    assert by_id["v1"].source == "both"
    assert by_id["v2"].source == "favorites"
    assert by_id["v3"].source == "liked"
    assert len(result) == 3


def test_merge_sources_deduplicates():
    favorites = [make_video("v1", "favorites")] * 3
    liked = [make_video("v1", "liked")]
    result = merge_sources(favorites, liked)
    assert len(result) == 1
    assert result[0].source == "both"
