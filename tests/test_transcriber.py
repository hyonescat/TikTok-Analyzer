import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.transcriber import get_transcript, _load_cached_transcript
from core.models import VideoRecord


def make_video(video_id="v1"):
    return VideoRecord(
        video_id=video_id, url="https://tiktok.com/@u/video/v1",
        caption="Dev setup", hashtags=[], source="favorites",
        author_username="u", author_display_name="U",
        like_count=0, comment_count=0, share_count=0, play_count=0,
    )


def test_load_cached_transcript_returns_none_when_missing(tmp_dir):
    result = _load_cached_transcript("v1", tmp_dir)
    assert result is None


def test_load_cached_transcript_returns_text_when_exists(tmp_dir):
    (tmp_dir / "v1.txt").write_text("hello world")
    result = _load_cached_transcript("v1", tmp_dir)
    assert result == "hello world"


def test_get_transcript_uses_cache(tmp_dir):
    (tmp_dir / "v1.txt").write_text("cached transcript")
    with patch("core.transcriber._download_and_transcribe") as mock:
        result = get_transcript(make_video(), tmp_dir, Path("cookies/cookies.txt"))
    mock.assert_not_called()
    assert result == "cached transcript"


def test_get_transcript_calls_download_when_no_cache(tmp_dir):
    with patch("core.transcriber._download_and_transcribe", return_value="new transcript") as mock:
        result = get_transcript(make_video(), tmp_dir, Path("cookies/cookies.txt"))
    mock.assert_called_once()
    assert result == "new transcript"
    assert (tmp_dir / "v1.txt").read_text() == "new transcript"


def test_get_transcript_returns_none_on_download_failure(tmp_dir):
    with patch("core.transcriber._download_and_transcribe", side_effect=RuntimeError("yt-dlp failed")):
        result = get_transcript(make_video(), tmp_dir, Path("cookies/cookies.txt"))
    assert result is None
